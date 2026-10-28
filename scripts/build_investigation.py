#!/usr/bin/env python3
"""Publish a verified immutable snapshot; never deploy WordPress."""
import argparse
from publish_release import publish
p = argparse.ArgumentParser()
p.add_argument('investigation',choices=['where-bills-go-to-die'])
p.parse_args()
publish()
