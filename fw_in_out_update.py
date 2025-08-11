import json
import datetime
import meraki
import os

def log_result(log_file, message):
    with open(log_file, 'a') as f:
        f.write(message + '\n')

def get_all_organizations(dashboard):
    return dashboard.organizations.getOrganizations()

def get_networks_in_org(dashboard, org_id):
    return dashboard.organizations.getOrganizationNetworks(org_id)

def filter_networks_by_tag(networks, tag):
    return [net for net in networks if tag in net.get('tags', [])]

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
    dry_run = input("Enable dry-run mode (no changes applied)? (y/n): ").strip().lower() == 'y'

    rules = load_rules_from_file(config_file)

    print(f"\n📋 Loaded {rule_type.capitalize()} Firewall Rules:\n")
    print(json.dumps(rules, indent=2))

    confirm = input("❓ Proceed with these firewall rules? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("⚠️ Aborted by user.")
        return

    # Note: adjust/remove certificate_path as appropriate for your environment
    dashboard = meraki.DashboardAPI(api_key, output_log=False, print_console=True)

    orgs = get_all_organizations(dashboard)
    print("\nAvailable Organizations:")
    for idx, org in enumerate(orgs):
        print(f"{idx + 1}: {org['name']} (ID: {org['id']})")
    org_index = int(input("Select an organization by number: ")) - 1
    org_id = orgs[org_index]['id']

    networks = get_networks_in_org(dashboard, org_id)

    tag_filter = input("\nEnter a Network Tag to filter by (or press Enter to skip): ").strip()
    if tag_filter:
        networks = filter_networks_by_tag(networks, tag_filter)
        if not networks:
            print(f"❌ No networks found with tag '{tag_filter}'.")
            return
        print(f"\nFiltered Networks with tag '{tag_filter}':")
    else:
        print("\nAll Networks:")

    for idx, net in enumerate(networks):
        print(f"{idx + 1}: {net['name']} (ID: {net['id']})")

    choice = input("\nDo you want to UPDATE firewall rules for ALL listed networks? (y/n): ").strip().lower()
    if choice == 'y':
        selected_networks = networks
    else:
        indices = input("Enter the numbers of the networks to update, separated by commas: ")
        indices = [int(i.strip()) - 1 for i in indices.split(',') if i.strip().isdigit()]
        selected_networks = [networks[i] for i in indices]

    # Prepare log + backup dir
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"firewall_update_log_{rule_type}_{timestamp}.txt"
    backup_dir = f"firewall_backups_{rule_type}_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    log_result(log_file, f"=== Firewall {rule_type.capitalize()} Update Log: {timestamp} ===")
    log_result(log_file, f"Dry Run Mode: {'YES' if dry_run else 'NO'}\n")

    # Final confirmation before applying
    print("\n🚨 FINAL CHECK")
    print("The script is about to apply changes to the following networks:")
    for net in selected_networks:
        print(f"- {net['name']} (ID: {net['id']})")

    final_confirm = input("\n⚠️ Are you sure you want to proceed with these changes? Type 'CONFIRM' to continue: ").strip()
    if final_confirm != 'CONFIRM':
        print("❌ Aborted by user at final validation step.")
        return

    # Apply changes
    for net in selected_networks:
        net_id = net['id']
        net_name = net['name']
        print(f"\n🔧 Processing: {net_name} (ID: {net_id})")

        if dry_run:
            msg = f"🟡 DRY RUN: Would update {rule_type} firewall rules for '{net_name}'"
            print(msg)
            log_result(log_file, msg)
            continue

        # Backup current rules (only when not dry-running to mirror alerts script behavior)
        success, result = backup_rules(dashboard, net_id, net_name, rule_type, backup_dir)
        if success:
            log_result(log_file, f"📦 Backed up current {rule_type} rules for '{net_name}' to: {result}")
        else:
            log_result(log_file, f"❌ Failed to backup {rule_type} rules for '{net_name}': {result}")
            # Skip updates if backup failed to avoid risk
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
