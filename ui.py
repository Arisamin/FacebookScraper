"""Launcher script for Facebook Scraper Desktop GUI."""

import sys
import os

# Ensure repository root is on Python sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.app import launch_ui

if __name__ == "__main__":
    launch_ui()
