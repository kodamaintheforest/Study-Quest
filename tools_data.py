# Seed tool lists. "learned" state is tracked separately in tools_state.json
# so re-running this file to add new tools later doesn't wipe your progress.

RED_KILLCHAIN = {
    "Recon": ["Nmap", "theHarvester", "Shodan", "Amass", "Recon-ng"],
    "Weaponization": ["Msfvenom", "Veil", "Shellter"],
    "Delivery": ["GoPhish", "Social Engineer Toolkit (SET)"],
    "Exploitation": ["Metasploit", "Burp Suite", "SQLmap"],
    "Installation": ["Mimikatz", "PsExec"],
    "Command & Control": ["Cobalt Strike", "Sliver", "Empire"],
    "Actions on Objectives": ["BloodHound", "Rubeus", "Impacket"],
}

BLUE_CATEGORIES = {
    "SIEM / Log Analysis": ["Splunk", "Elastic (ELK) Stack", "Graylog"],
    "Network Detection": ["Wireshark", "Suricata", "Zeek"],
    "Endpoint / EDR": ["Velociraptor", "OSQuery", "Sysmon"],
    "Forensics": ["Autopsy", "Volatility", "FTK Imager"],
    "Threat Intel": ["MISP", "VirusTotal", "AlienVault OTX"],
}


def build_initial_state():
    state = {"red": {}, "blue": {}}
    for phase, tools in RED_KILLCHAIN.items():
        state["red"][phase] = {tool: False for tool in tools}
    for category, tools in BLUE_CATEGORIES.items():
        state["blue"][category] = {tool: False for tool in tools}
    return state
