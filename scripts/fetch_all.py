from .fetch_ansi_up import main as ansi_up_main
from .fetch_bootstrap import main as bootstrap_main
from .fetch_codemirror import main as codemirror_main
from .fetch_js_yaml import main as js_yaml_main
from .fetch_mdi import main as mdi_main

def main():
    ansi_up_main()
    bootstrap_main()
    codemirror_main()
    js_yaml_main()
    mdi_main()

if __name__ == "__main__":
    main()