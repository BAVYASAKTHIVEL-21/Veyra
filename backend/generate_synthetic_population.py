
import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "synthetic_scenarios.json"
TARGET_ACCOUNTS = 500
SEED = 42

rng = random.Random(SEED)


def next_id(prefix, used):
    number = 1
    while f"{prefix}_{number:06d}" in used:
        number += 1
    value = f"{prefix}_{number:06d}"
    used.add(value)
    return value


def main():
    # Prevent accidental repeated population generation.
    if DATA_FILE.exists():
        with DATA_FILE.open(encoding="utf-8") as f:
            existing_data = json.load(f)

        if existing_data.get("population_generator_version") == 1:
            print("Population already generated. No changes made.")
            return
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if data.get("is_synthetic") is not True:
        raise ValueError("Refusing to modify a non-synthetic dataset.")

    accounts = data["accounts"]
    posts = data["posts"]
    relationships = data["relationships"]

    # Preserve all existing entities and their IDs.
    entity_collections = [
        "platforms", "scenarios", "accounts", "domains", "brands",
        "payment_identifiers", "posts", "evidence", "reports",
    ]
    entity_ids = {
        item["id"]
        for collection in entity_collections
        for item in data.get(collection, [])
        if item.get("id")
    }
    relationship_ids = {r["id"] for r in relationships}

    if len(entity_ids) != sum(
        len(data.get(k, [])) for k in entity_collections
    ):
        raise ValueError(
            "Existing entity IDs may collide. Resolve before generating."
        )
    if len(relationship_ids) != len(relationships):
        raise ValueError("Existing relationship IDs are not unique.")

    # Add a message collection if the dataset doesn't have one yet.
    messages = data.setdefault("messages", [])
    if any(not m.get("id") for m in messages):
        raise ValueError("Every existing message must have an ID.")

    message_ids = {m["id"] for m in messages}
    if len(message_ids) != len(messages):
        raise ValueError("Existing message IDs are not unique.")
    if entity_ids.intersection(message_ids):
        raise ValueError("Message IDs collide with existing entity IDs.")
    entity_ids.update(message_ids)

    # Ensure all new accounts receive appropriate account types.
    existing_usernames = {
        a.get("username", "").lower() for a in accounts
    }
    if len(existing_usernames) != len(accounts):
        raise ValueError("Existing account usernames are not unique.")

    first_names = [
        "Aanya", "Rohan", "Meera", "Kavin", "Ishita", "Arjun",
        "Nila", "Dev", "Priya", "Aditya", "Sara", "Vikram",
        "Ananya", "Rahul", "Diya", "Mira", "Kabir", "Tara",
        "Neha", "Aarav", "Ira", "Reyansh", "Kiara", "Yash",
    ]

    # Final target distribution for 500 accounts.
    desired_final = {
        "normal_user": 300,
        "creator": 70,
        "business": 60,
        "brand_support": 30,
        "suspicious_test": 40,
    }

    existing_count = len(accounts)
    if existing_count > TARGET_ACCOUNTS:
        raise ValueError("Existing account count exceeds target.")

    remaining = TARGET_ACCOUNTS - existing_count
    total_target = sum(desired_final.values())

    # Preserve original accounts and allocate the remaining slots.
    type_queue = []
    for kind, target_count in desired_final.items():
        allocation = round(target_count * remaining / total_target)
        type_queue.extend([kind] * allocation)

    # Ensure exactly the required number of new accounts.
    while len(type_queue) > remaining:
        type_queue.pop()
    while len(type_queue) < remaining:
        type_queue.append("normal_user")

    rng.shuffle(type_queue)

    type_by_id = {
        a["id"]: a.get("account_type", "existing")
        for a in accounts
    }

    for index in range(remaining):
        kind = type_queue[index]
        first = first_names[index % len(first_names)]
        username = f"{first.lower()}{index + 1:04d}"

        while username.lower() in existing_usernames:
            username += f"_{rng.randrange(1000, 9999)}"
        existing_usernames.add(username.lower())

        account_id = next_id("acct", entity_ids)
        platform_id = rng.choice([
            "platform_demosocial",
            "platform_demochat",
            "platform_demovideo",
        ])

        created = date(2023, 1, 1) + timedelta(
            days=rng.randrange(1300)
        )

        display_names = {
            "normal_user": first,
            "creator": f"{first} Creates",
            "business": f"{first}'s Market",
            "brand_support": f"{first} Support",
            "suspicious_test": f"{first} Offers",
        }
        bios = {
            "normal_user": "Synthetic demo social profile.",
            "creator": "Synthetic demo creator account.",
            "business": "Synthetic demo business account.",
            "brand_support": "Synthetic demo customer support account.",
            "suspicious_test": (
                "Synthetic security-test account; not a real person."
            ),
        }

        accounts.append({
            "id": account_id,
            "scenario_id": (
                "scenario_003"
                if kind == "suspicious_test"
                else "scenario_004"
            ),
            "platform_id": platform_id,
            "platform_account_id": f"demo_{account_id}",
            "username": username,
            "display_name": display_names[kind],
            "bio": bios[kind],
            "followers": rng.randrange(0, 20000),
            "following": rng.randrange(0, 1500),
            "post_count": 0,
            "verified": (
                kind in ("business", "brand_support")
                and rng.random() < 0.2
            ),
            "account_created_at": created.isoformat(),
            "account_status": (
                "under_review"
                if kind == "suspicious_test" and rng.random() < 0.4
                else "active"
            ),
            "profile_url": (
                f"https://{platform_id.removeprefix('platform_')}"
                f".example/@{username}"
            ),
            "is_synthetic": True,
            "account_type": kind,
        })
        type_by_id[account_id] = kind

    account_ids = [a["id"] for a in accounts]

    # Preserve original relationships and avoid duplicate directed edges.
    edge_keys = {
        (r["from"], r["type"], r["to"]) for r in relationships
    }

    def add_edge(source, rel_type, target):
        if source not in entity_ids or target not in entity_ids:
            raise ValueError(
                f"Relationship endpoint missing: {source} -> {target}"
            )
        key = (source, rel_type, target)
        if key in edge_keys:
            return
        relationships.append({
            "id": next_id("rel", relationship_ids),
            "from": source,
            "type": rel_type,
            "to": target,
        })
        edge_keys.add(key)

    # Normal users should form the majority of social interactions.
    normal_ids = [
        a["id"] for a in accounts
        if type_by_id.get(a["id"]) in ("normal_user", "friend", "existing")
    ]

    # FRIENDS_WITH is reciprocal to represent mutual friendship.
    for _ in range(min(650, len(normal_ids) * 3)):
        if len(normal_ids) < 2:
            break
        a, b = rng.sample(normal_ids, 2)
        add_edge(a, "FRIENDS_WITH", b)
        add_edge(b, "FRIENDS_WITH", a)

    # Create posts with the existing post schema.
    new_post_ids = []
    captions = [
        "A little update from today.",
        "Sharing something I enjoyed this week.",
        "New project, learning, and progress.",
        "Weekend moments with friends.",
        "A useful tip I wanted to share.",
    ]

    for _ in range(220):
        owner = rng.choice(account_ids)
        post_id = next_id("post", entity_ids)
        post = {
            "id": post_id,
            "scenario_id": "scenario_004",
            "account_id": owner,
            "platform_id": next(
                a["platform_id"] for a in accounts if a["id"] == owner
            ),
            "content_type": "social_post",
            "caption": rng.choice(captions),
            "content_hash": f"synthetic_hash_{post_id}",
            "media_path": None,
            "published_at": (
                date(2025, 1, 1) + timedelta(days=rng.randrange(650))
            ).isoformat(),
            "is_synthetic": True,
        }
        posts.append(post)
        new_post_ids.append(post_id)
        add_edge(owner, "CREATED_POST", post_id)

    # Add comments only as edges to existing posts.
    all_post_ids = [p["id"] for p in posts]
    post_owner = {p["id"]: p["account_id"] for p in posts}

    for _ in range(350):
        if not all_post_ids:
            break
        post_id = rng.choice(all_post_ids)
        candidates = [a for a in account_ids if a != post_owner[post_id]]
        if candidates:
            add_edge(rng.choice(candidates), "COMMENTS_ON", post_id)

    # Create persisted messages and sender -> message -> recipient links.
    for _ in range(500):
        sender, recipient = rng.sample(account_ids, 2)
        message_id = next_id("message", entity_ids)
        message = {
            "id": message_id,
            "sender_id": sender,
            "recipient_id": recipient,
            "text": rng.choice([
                "Hey, how was your day?",
                "Thanks for sharing the update!",
                "Are we still meeting this weekend?",
                "I found this useful and thought of you.",
                "Could you share more details?",
            ]),
            "scenario_id": "scenario_004",
            "is_synthetic": True,
            "created_at": (
                date(2025, 1, 1) + timedelta(days=rng.randrange(650))
            ).isoformat(),
        }
        messages.append(message)
        add_edge(sender, "SENDS_MESSAGE", message_id)
        add_edge(message_id, "SENT_TO", recipient)


    # Domain sharing must correspond to a real URL in the message.
    # Sharing a domain alone is not evidence of suspicious behavior.
    domains = data.get("domains", [])

    if domains:
        eligible_accounts = [
            a for a in accounts
            if type_by_id.get(a["id"]) in (
                "normal_user", "creator", "business"
            )
        ]

        for account in eligible_accounts:
            if rng.random() >= 0.06:
                continue

            domain = rng.choice(domains)
            domain_id = domain["id"]
            domain_name = domain.get("name") or domain.get("domain")

            if not domain_name:
                continue

            recipient_candidates = [
                account_id for account_id in account_ids
                if account_id != account["id"]
            ]
            if not recipient_candidates:
                continue

            recipient = rng.choice(recipient_candidates)
            message_id = next_id("message", entity_ids)

            message = {
                "id": message_id,
                "sender_id": account["id"],
                "recipient_id": recipient,
                "text": f"Sharing this website: https://{domain_name}",
                "domain_id": domain_id,
                "scenario_id": "scenario_004",
                "is_synthetic": True,
                "created_at": now_date(),
            }

            messages.append(message)
            add_edge(account["id"], "SENDS_MESSAGE", message_id)
            add_edge(message_id, "SENT_TO", recipient)
            add_edge(account["id"], "SHARES_DOMAIN", domain_id)


    # Validate every endpoint against entity IDs and message IDs.
    all_ids = set(entity_ids)
    all_ids.update(message_ids)
    all_ids.update(m["id"] for m in messages)
    for collection in entity_collections:
        all_ids.update(x["id"] for x in data.get(collection, []) if x.get("id"))

    invalid = [
        r for r in relationships
        if r["from"] not in all_ids or r["to"] not in all_ids
    ]
    if invalid:
        raise ValueError(f"Invalid relationship endpoints: {invalid[:5]}")

    if len({a["id"] for a in accounts}) != len(accounts):
        raise ValueError("Duplicate account IDs.")
    if len({p["id"] for p in posts}) != len(posts):
        raise ValueError("Duplicate post IDs.")
    if len({m["id"] for m in messages}) != len(messages):
        raise ValueError("Duplicate message IDs.")
    if len({r["id"] for r in relationships}) != len(relationships):
        raise ValueError("Duplicate relationship IDs.")

    # Dry run: validate generated data without writing to disk.
    import sys
    if "--dry-run" in sys.argv:
        print("Dry-run validation succeeded. No files were changed.")
        print("Accounts:", len(accounts))
        print("Posts:", len(posts))
        print("Messages:", len(messages))
        print("Relationships:", len(relationships))
        print("Relationship types:", dict(Counter(r["type"] for r in relationships)))
        return

    # Store the new collection in the dataset.
    data["messages"] = messages
    data["population_generator_version"] = 1

    # Atomic replacement: write a temporary file and then replace the JSON.
    temp_file = DATA_FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    backup = DATA_FILE.with_suffix(".json.bak")
    if not backup.exists():
        backup.write_text(
            DATA_FILE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    temp_file.replace(DATA_FILE)

    print("Generation and validation succeeded.")
    print("Accounts:", len(accounts))
    print("Posts:", len(posts))
    print("Messages:", len(messages))
    print("Relationships:", len(relationships))
    print("Relationship types:", dict(Counter(r["type"] for r in relationships)))
    print("Backup:", backup)


def now_date():
    return date.today().isoformat()


if __name__ == "__main__":
    main()
