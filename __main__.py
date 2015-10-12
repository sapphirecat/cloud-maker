import runpy
import sys

# module maps
explanations = {
    'make_provisioner': 'Creates a self-extracting installer from a directory',
    'fedora2ova': 'Builds an OVA from a raw *.img fedora-cloud image',
}
aliases = {
    'provision': 'make_provisioner',
}

try:
    wanted = sys.argv[1]
    if wanted in explanations:
        mod = wanted
    else:
        mod = aliases[wanted]
except KeyError:
    mod = None

if mod is not None:
    sys.argv[1:2] = [] # delete module name, pass all other args straight through
    runpy.run_module(mod)
    sys.exit(0)
else:
    if wanted is not None and wanted != '-h' and 'help' not in wanted:
        print("Unrecognized command: {}".format(wanted), file=sys.stderr, end="\n\n")
    usage = [
        "cloud-maker: a zip/dir bundle of cloud tools", "",
        "Usage: {} COMMAND [command's options]".format(sys.argv[0]), "",
        "Known commands (try `COMMAND --help` for more on a command):", "",
    ]
    for line in usage:
        print(line)
    # gather up the aliases for a command
    alias_map = dict((k, set()) for k in explanations.keys())
    for k,v in aliases.items():
        alias_map[v].add(k)
    # show commands+aliases
    for cmd in sorted(explanations.keys()):
        print("\t{}: {}".format(cmd, explanations[cmd]))
        if alias_map[cmd]:
            print("\t\taliases: ", ", ".join(alias_map[cmd]))
    sys.exit(0)
