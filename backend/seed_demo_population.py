
from graph.connection import get_graph

# All records are synthetic. IDs remain stable across runs.
graph = get_graph()

accounts = [
    {
        "id": "acct_friend_001",
        "username": "maya_friends",
        "display_name": "Maya",
        "account_type": "friend",
        "scenario_type": "normal_friend",
        "reputation_status": "unverified",
        "is_synthetic": True,
    },
    {
        "id": "acct_friend_002",
        "username": "arjun_connect",
        "display_name": "Arjun",
        "account_type": "friend",
        "scenario_type": "simulated_compromised_friend",
        "reputation_status": "under_review",
        "is_synthetic": True,
    },
    {
        "id": "acct_unknown_001",
        "username": "quick_reward_24",
        "display_name": "Quick Rewards",
        "account_type": "unknown",
        "scenario_type": "suspicious_link",
        "reputation_status": "under_review",
        "is_synthetic": True,
    },
    {
        "id": "acct_business_001",
        "username": "earthkind_market",
        "display_name": "Earthkind Market",
        "account_type": "business",
        "scenario_type": "legitimate_business",
        "reputation_status": "unverified",
        "is_synthetic": True,
    },
    {
        "id": "acct_brand_001",
        "username": "nordvale_prize",
        "display_name": "Nordvale Prize Support",
        "account_type": "business",
        "scenario_type": "possible_brand_impersonation",
        "reputation_status": "under_review",
        "is_synthetic": True,
    },
    {
        "id": "acct_authority_001",
        "username": "official_case_desk",
        "display_name": "Case Verification Desk",
        "account_type": "unknown",
        "scenario_type": "virtual_arrest_scam",
        "reputation_status": "under_review",
        "is_synthetic": True,
    },
]

domains = [
    {
        "id": "domain_friend_001",
        "domain": "shared-reward.example",
        "scenario_type": "simulated_suspicious_domain",
        "is_synthetic": True,
    },
    {
        "id": "domain_brand_001",
        "domain": "nordvale-prize.example",
        "scenario_type": "simulated_brand_impersonation",
        "is_synthetic": True,
    },
    {
        "id": "domain_business_001",
        "domain": "earthkind.example",
        "scenario_type": "legitimate_style_example",
        "is_synthetic": True,
    },
]

messages = [
    {
        "id": "msg_001",
        "sender_id": "acct_friend_001",
        "text": "Bro, here are the notes from today's meeting.",
        "scenario_type": "benign_message",
        "expected_outcome": "no_warning_indicators",
    },
    {
        "id": "msg_002",
        "sender_id": "acct_friend_002",
        "text": "Hey, check out these free rewards: https://shared-reward.example",
        "domain_id": "domain_friend_001",
        "scenario_type": "simulated_compromised_friend",
        "expected_outcome": "investigate_link",
    },
    {
        "id": "msg_003",
        "sender_id": "acct_unknown_001",
        "text": "Your account will be suspended. Verify immediately at https://shared-reward.example",
        "domain_id": "domain_friend_001",
        "scenario_type": "urgent_phishing_indicators",
        "expected_outcome": "potential_warning",
    },
    {
        "id": "msg_004",
        "sender_id": "acct_business_001",
        "text": "Your order update is available. Please review your order details.",
        "scenario_type": "legitimate_business_message",
        "expected_outcome": "no_warning_indicators",
    },
    {
        "id": "msg_005",
        "sender_id": "acct_brand_001",
        "text": "Pay a processing fee to claim your exclusive prize at https://nordvale-prize.example",
        "domain_id": "domain_brand_001",
        "scenario_type": "possible_brand_impersonation",
        "expected_outcome": "investigate_brand_and_domain",
    },
    {
        "id": "msg_006",
        "sender_id": "acct_authority_001",
        "text": "You are under investigation. Send money immediately or face arrest.",
        "scenario_type": "virtual_arrest_threat",
        "expected_outcome": "high_priority_safety_review",
    },
    {
        "id": "msg_007",
        "sender_id": "acct_friend_002",
        "text": "Please check this reward link before opening it: https://shared-reward.example",
        "domain_id": "domain_friend_001",
        "scenario_type": "repeated_link_sharing",
        "expected_outcome": "investigate_shared_domain",
    },
]

reporters = [
    {"id": "reporter_001", "is_synthetic": True},
    {"id": "reporter_002", "is_synthetic": True},
    {"id": "reporter_003", "is_synthetic": True},
]

reports = [
    {
        "id": "demo_report_001",
        "account_id": "acct_friend_002",
        "reporter_id": "reporter_001",
        "message_id": "msg_002",
        "reason": "Unexpected suspicious link from a known contact",
        "status": "unverified",
    },
    {
        "id": "demo_report_002",
        "account_id": "acct_friend_002",
        "reporter_id": "reporter_002",
        "message_id": "msg_007",
        "reason": "Repeated sharing of the same suspicious domain",
        "status": "under_review",
    },
    {
        "id": "demo_report_003",
        "account_id": "acct_friend_002",
        "reporter_id": "reporter_003",
        "message_id": "msg_002",
        "reason": "Reported link in a separate synthetic user report",
        "status": "unverified",
    },
    {
        "id": "demo_report_004",
        "account_id": "acct_authority_001",
        "reporter_id": "reporter_001",
        "message_id": "msg_006",
        "reason": "Threatening message demanding payment",
        "status": "under_review",
    },
]



def merge_node(label, record):
    # Labels are fixed in this script, never supplied by a user.
    props = {k: v for k, v in record.items() if k != "id"}
    graph.query(
        f"MERGE (n:Entity:{label} {{id: $id}}) "
        "SET n += $props",
        {"id": record["id"], "props": props},
    )


def merge_edge(source_label, source_id, rel_type,
               target_label, target_id, rel_id):
    graph.query(
        f"MATCH (a:Entity:{source_label} {{id: $source_id}}) "
        f"MATCH (b:Entity:{target_label} {{id: $target_id}}) "
        f"MERGE (a)-[r:{rel_type} {{id: $rel_id}}]->(b)",
        {
            "source_id": source_id,
            "target_id": target_id,
            "rel_id": rel_id,
        },
    )


# Create accounts and domains first.
for account in accounts:
    merge_node("Account", account)

for domain in domains:
    merge_node("Domain", domain)

for reporter in reporters:
    merge_node("Reporter", reporter)

# Messages are persisted as graph entities.
for message in messages:
    props = {
        k: v for k, v in message.items()
        if k not in ("id", "sender_id", "domain_id")
    }
    merge_node("Message", {"id": message["id"], **props})
    merge_edge(
        "Account", message["sender_id"],
        "SENT", "Message", message["id"],
        f"sent_{message['id']}",
    )

    domain_id = message.get("domain_id")
    if domain_id:
        merge_edge(
            "Message", message["id"],
            "CONTAINS_LINK", "Domain", domain_id,
            f"link_{message['id']}",
        )
        merge_edge(
            "Account", message["sender_id"],
            "SHARES_DOMAIN", "Domain", domain_id,
            f"shares_{message['id']}",
        )

# Reports link distinct synthetic reporters to accounts and messages.
for report in reports:
    props = {
        k: v for k, v in report.items()
        if k not in ("id", "account_id", "reporter_id", "message_id")
    }
    merge_node("Report", {"id": report["id"], **props})

    merge_edge(
        "Report", report["id"],
        "REPORTS_ACCOUNT", "Account", report["account_id"],
        f"report_account_{report['id']}",
    )
    merge_edge(
        "Report", report["id"],
        "SUBMITTED_BY", "Reporter", report["reporter_id"],
        f"reporter_link_{report['id']}",
    )
    merge_edge(
        "Report", report["id"],
        "ABOUT_MESSAGE", "Message", report["message_id"],
        f"report_message_{report['id']}",
    )

print("Synthetic Veyra demo population seeded.")
print(f"Accounts: {len(accounts)}")
print(f"Domains: {len(domains)}")
print(f"Messages: {len(messages)}")
print(f"Reports: {len(reports)}")
