import sys
import streamlit.web.cli as stcli

# Main logic
if __name__ == '__main__':
    sys.argv = ["streamlit", "run", "main.py"]
    sys.exit(stcli.main())