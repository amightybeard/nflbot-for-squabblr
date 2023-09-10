name: Game Thread Updater

on:
  workflow_dispatch:  # This allows you to manually trigger the workflow from the GitHub Actions UI
  # schedule:
    # - cron: '0 22 * * 4' # 6pm ET on Thursda

jobs:
  update-game-thread:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repository
      uses: actions/checkout@v2

    - name: Set up Python 3.8
      uses: actions/setup-python@v2
      with:
        python-version: 3.8

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests

    - name: Run gamethread-updater.py
      run: python gamethread-updater.py
      env:
        SQUABBLES_TOKEN: ${{ secrets.SQUABBLES_TOKEN }}
        NFLBOT_WRITE_TO_GIST: ${{ secrets.NFLBOT_WRITE_TO_GIST }}  # Using the GitHub token from repository secrets
