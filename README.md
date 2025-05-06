## Meraki Firewall Rule Automation Script

This Python script automates the process of updating **Inbound** or **Outbound** firewall rules on Cisco Meraki networks filtered by a **specific network tag** within an organzation, within networks. 

 ### Features

- Supports both **Inbound** and **Outbound** firewall rules
- Targets networks by **custom tag**
- Logs
- Automatically backs up current firewall rules before making changes
- Optional **dry-run** mode to simulate changes without applying them

---

### Requirements

- Python 3.7+
- Meraki Dashboard API Key
- JSON templates with desired firewall configuration

### Use
- It is recommended to save the JSON file/s in the same folder as the script. You will need this PATH in order to tell the program where to find it.
- To use an Object or Group the IDs need to be retrieved in the web browser using Inspect or querying the dashboard with API dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules for example. 
- If not certificate is needed, then the '../../certificate' should be removed. 