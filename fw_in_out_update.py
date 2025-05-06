import json
import datetime
import meraki
import os

def log_result(log_file, message):
    with open(log_file, 'a') as f:
        f.write(message + '\n')

def get_all_organizations(dashboard):
    return dashboard.organizations.getOrganizations()

def get_networks_by_tag(dashboard, org_id, tag):
    all_networks = dashboard.organizations.getOrganizationNetworks(org_id)
    return [net for net in all_networks if tag in net.get('tags', [])]

def load_rules_from_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def backup_rules(dashboard, network_id, net_name, rule_type, backup_dir):
    try:
        if rule_type == 'outbound':
            current_rules = dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules(network_id)
        else:  # inbound
            current_rules = dashboard.appliance.getNetworkApplianceFirewallInboundFirewallRules(network_id)

        filename = os.path.join(backup_dir, f"{net_name.replace(' ', '_')}_{network_id}_{rule_type}_backup.json")
        with open(filename, 'w') as f:
            json.dump(current_rules, f, indent=2)
        return True, filename
    except Exception as e:
        return False, str(e)

def update_rules(dashboard, network_id, rule_type, rules):
    try:
        if rule_type == 'outbound':
            dashboard.appliance.updateNetworkApplianceFirewallL3FirewallRules(
                network_id,
                rules=rules
            )
        else:  # inbound
            dashboard.appliance.updateNetworkApplianceFirewallInboundFirewallRules(
                network_id,
                rules=rules
            )
        return True
    except Exception as e:
        print(f"❌ Error updating {rule_type.upper()} firewall rules for network {network_id}: {e}")
        return False

def main():
    api_key = input("Enter your Meraki Dashboard API Key: ").strip()
    rule_type = input("Do you want to update Inbound or Outbound firewall rules? (inbound/outbound): ").strip().lower()
    if rule_type not in ['inbound', 'outbound']:
        print("❌ Invalid option. Must be 'inbound' or 'outbound'.")
        return

    config_file = input(f"Enter path to {rule_type} firewall rules JSON file: ").strip()
    network_tag = input("Enter the Network Tag to filter networks: ").strip()
    dry_run = input("Enable dry-run mode (no changes applied)? (y/n): ").strip().lower() == 'y'

    rules = load_rules_from_file(config_file)

    print(f"\n📋 Loaded {rule_type.capitalize()} Firewall Rules:\n")
    print(json.dumps(rules, indent=2))

    confirm = input("❓ Proceed with these firewall rules? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("⚠️ Aborted by user.")
        return

    dashboard = meraki.DashboardAPI(api_key, output_log=False, print_console=True, certificate_path='../../certificate.pem')

    orgs = get_all_organizations(dashboard)
    print("\nAvailable Organizations:")
    for idx, org in enumerate(orgs):
        print(f"{idx + 1}: {org['name']} (ID: {org['id']})")
    org_index = int(input("Select an organization by number: ")) - 1
    org_id = orgs[org_index]['id']

    tagged_networks = get_networks_by_tag(dashboard, org_id, network_tag)
    if not tagged_networks:
        print(f"❌ No networks found with tag '{network_tag}'.")
        return

    print(f"\nNetworks with tag '{network_tag}':")
    for idx, net in enumerate(tagged_networks):
        print(f"{idx + 1}: {net['name']} (ID: {net['id']})")

    choice = input("Do you want to UPDATE firewall rules for ALL tagged networks? (y/n): ").strip().lower()
    if choice == 'y':
        selected_networks = tagged_networks
    else:
        indices = input("Enter the numbers of the networks to update, separated by commas: ")
        indices = [int(i.strip()) - 1 for i in indices.split(',') if i.strip().isdigit()]
        selected_networks = [tagged_networks[i] for i in indices]

    final_confirm = input("\n⚠️ Type 'CONFIRM' to apply the firewall rules to these networks: ").strip()
    if final_confirm != 'CONFIRM':
        print("❌ Aborted by user at final step.")
        return

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"firewall_update_log_{rule_type}_{timestamp}.txt"
    backup_dir = f"firewall_backups_{rule_type}_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    log_result(log_file, f"=== Firewall {rule_type.capitalize()} Update Log: {timestamp} ===")
    log_result(log_file, f"Dry Run Mode: {'YES' if dry_run else 'NO'}")
    log_result(log_file, f"Target Networks (tag={network_tag}): {len(tagged_networks)}\n")

    for net in selected_networks:
        net_id = net['id']
        net_name = net['name']
        print(f"\n🔧 Processing: {net_name} (ID: {net_id})")

        # Backup current rules
        success, result = backup_rules(dashboard, net_id, net_name, rule_type, backup_dir)
        if success:
            log_result(log_file, f"📦 Backed up current {rule_type} rules for '{net_name}' to: {result}")
        else:
            log_result(log_file, f"❌ Failed to backup {rule_type} rules for '{net_name}': {result}")
            continue

        if dry_run:
            log_result(log_file, f"🟡 DRY RUN: Would apply {rule_type} firewall rules to '{net_name}'")
            continue

        # Apply new rules
        updated = update_rules(dashboard, net_id, rule_type, rules)
        if updated:
            log_result(log_file, f"✅ Updated {rule_type} firewall rules for '{net_name}'")
        else:
            log_result(log_file, f"❌ Failed to update {rule_type} firewall rules for '{net_name}'")

    print(f"\n📝 Log saved to: {log_file}")
    print(f"🗂️ Backups saved in: {backup_dir}")

if __name__ == "__main__":
    main()