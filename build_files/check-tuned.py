#!/usr/bin/python3 -I
"""Build test: every power mode tuned-ppd switches to loads with tuned's bootloader unit turned off."""
import configparser
import sys

from tuned import consts, profiles
from tuned.profiles.variables import Variables
from tuned.utils.global_config import GlobalConfig

ppd = configparser.ConfigParser()
ppd.read("/etc/tuned/ppd.conf")
modes = {mode for section in ("profiles", "battery") for mode in ppd[section].values()}
if not modes:
    sys.exit("ERROR: no power modes found in /etc/tuned/ppd.conf")
with open(consts.POST_LOADED_PROFILE_FILE) as f:
    post_loaded = f.read().strip()

cfg = GlobalConfig()
locator = profiles.Locator(cfg.get_list(consts.CFG_PROFILE_DIRS, consts.CFG_DEF_PROFILE_DIRS))
loader = profiles.Loader(locator, profiles.Factory(), profiles.Merger(), cfg, Variables())
for mode in sorted(modes):
    unit = loader.load([mode, post_loaded]).units.get("bootloader")
    if unit is None or unit.enabled:
        sys.exit(f"ERROR: power mode {mode} would still run bootc on every switch")
print(f"Power modes {', '.join(sorted(modes))} load with tuned's bootloader unit off")
