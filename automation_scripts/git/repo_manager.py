#!/usr/bin/env python3
"""
Script Name: repo_manager.py
Purpose: Git repository management for ANITA project
Date: March 24, 2025
"""

import os
import subprocess
import sys
import time
import datetime
import logging
import webbrowser
import platform
import argparse
from pathlib import Path

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))  # Parent directory of automation_scripts

# Set log file in central logs directory
LOG_DIR = os.path.join(REPO_DIR, 'logs', 'active')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'repo_manager.log')

GITHUB_REPO_URL = "https://github.com/MasterNineteen82/anita.git"
BRANCH = 'main'
CREDENTIAL_HELPER = 'cache' if platform.system() != 'Windows' else 'wincred'

# Set up logging with fallback
try:
    # Try to use the project's logging config
    sys.path.insert(0, REPO_DIR)
    from backend.logging.logging_config import setup_logging
    logger = setup_logging()
except ImportError:
    # Fallback to basic logging if the import fails
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Using fallback logging configuration")

def log_message(message, level=logging.INFO):
    """Log a message both to file and console"""
    logger.log(level, message)
    # Ensure it's printed immediately
    print(message)

def run_command(command, show_output=True):
    """Run a command and return the result"""
    try:
        log_message(f"Running command: {command}" if show_output else "Running command...")
        
        # Use subprocess to run the command
        process = subprocess.run(
            command,
            cwd=REPO_DIR,
            shell=True,
            text=True,
            capture_output=True
        )
        
        # Check if the command was successful
        if process.returncode == 0:
            if show_output and process.stdout:
                log_message(process.stdout.strip())
            return True, process.stdout.strip()
        else:
            log_message(f"Command failed with return code {process.returncode}", logging.ERROR)
            log_message(f"Error: {process.stderr.strip()}", logging.ERROR)
            return False, process.stderr.strip()
            
    except Exception as e:
        log_message(f"Exception running command: {str(e)}", logging.ERROR)
        return False, str(e)

def check_for_conflicts():
    """Check for git merge conflicts"""
    success, output = run_command("git diff --name-only --diff-filter=U", show_output=False)
    if output:
        log_message("⚠️ Merge conflicts detected in these files:", logging.WARNING)
        for file in output.split("\n"):
            if file.strip():
                log_message(f"  - {file}", logging.WARNING)
        return True
    return False

def setup_credential_helper():
    """Configure git credential helper for smoother authentication"""
    log_message("Setting up credential helper...")
    success, _ = run_command(f"git config --global credential.helper {CREDENTIAL_HELPER}")
    if success:
        log_message("Credential helper configured. Your credentials will be cached for future use.")
    else:
        log_message("Failed to set up credential helper.", logging.WARNING)

def is_git_repo():
    """Check if the directory is a Git repository"""
    success, _ = run_command("git rev-parse --is-inside-work-tree", show_output=False)
    return success

def init_git_repo():
    """Initialize a new Git repository"""
    log_message("Initializing Git repository...")
    success, output = run_command("git init")
    
    if not success:
        log_message("Failed to initialize Git repository.", logging.ERROR)
        return False
        
    log_message("Git repository initialized successfully.")
    
    # Configure user details if needed
    config_user()
    
    # Set up credential helper for smoother authentication
    setup_credential_helper()
    
    return True

def config_user():
    """Configure Git user details if not already set"""
    # Check if user details are already configured
    success, output = run_command("git config --get user.name", show_output=False)
    if not success or not output:
        # Name not configured, ask for it
        name = input("Enter your name for Git commits: ")
        if name:
            run_command(f'git config --global user.name "{name}"')
    
    success, output = run_command("git config --get user.email", show_output=False)
    if not success or not output:
        # Email not configured, ask for it
        email = input("Enter your email for Git commits: ")
        if email:
            run_command(f'git config --global user.email "{email}"')

def setup_remote(use_github_desktop=True):
    """Set up remote repository"""
    # Check if remote already exists
    success, output = run_command("git remote -v", show_output=False)
    
    if success and "origin" in output:
        log_message("Remote 'origin' already exists.")
        return True
        
    # Different approaches based on preference
    if use_github_desktop:
        # Open GitHub Desktop for a more user-friendly experience
        return setup_with_github_desktop()
    else:
        # Direct command-line setup
        return setup_with_command_line()

def setup_with_github_desktop():
    """Set up repository using GitHub Desktop"""
    log_message("Opening GitHub Desktop to set up your repository...")
    
    # Try to launch GitHub Desktop with this repository
    try:
        # First, create a dummy commit so GitHub Desktop can pick up the repo
        run_command("git add .")
        run_command('git commit --allow-empty -m "Initial commit"')
        
        # Try to open with GitHub Desktop's URL protocol
        webbrowser.open(f"github-desktop://openRepository/{REPO_DIR}")
        
        log_message("\n" + "-"*50)
        log_message("GitHub Desktop should be opening. Please follow these steps:")
        log_message("1. When GitHub Desktop opens, choose 'Publish this repository to GitHub'")
        log_message("2. Enter repository details and complete the setup")
        log_message("3. Come back to this window when finished")
        log_message("-"*50 + "\n")
        
        # Wait for user confirmation
        input("Press Enter once you've set up the repository in GitHub Desktop...")
        
        # Verify setup worked
        success, output = run_command("git remote -v", show_output=False)
        if success and "origin" in output:
            log_message("Remote repository configured successfully!")
            return True
        else:
            log_message("Remote repository configuration not detected.", logging.WARNING)
            return False
            
    except Exception as e:
        log_message(f"Error opening GitHub Desktop: {str(e)}", logging.ERROR)
        log_message("Please open GitHub Desktop manually and add this repository.")
        return False

def setup_with_command_line():
    """Set up repository using command line Git"""
    # Ask for repository URL
    repo_url = input(f"Enter the remote repository URL (or press Enter for {GITHUB_REPO_URL}): ")
    if not repo_url:
        repo_url = GITHUB_REPO_URL
        
    # Add the remote
    success, output = run_command(f"git remote add origin {repo_url}")
    
    if not success:
        log_message("Failed to add remote repository.", logging.ERROR)
        return False
        
    log_message("Remote repository added successfully.")
    return True

def update_repo(use_github_desktop=True, skip_prompt=False):
    """Update the Git repository"""
    log_message("\n" + "="*50)
    log_message("Starting Git update process...")
    log_message("="*50)
    
    # First, check if this is a Git repository
    if not is_git_repo():
        log_message("This directory is not a Git repository.", logging.WARNING)
        
        # Ask to initialize
        if skip_prompt:
            response = 'y'
        else:
            response = input("Do you want to initialize a Git repository here? (y/n): ")
        
        if response.lower() != 'y':
            log_message("Aborting update.")
            return False
            
        # Initialize repository
        if not init_git_repo():
            return False
            
        # Set up remote
        if not setup_remote(use_github_desktop):
            log_message("Remote setup incomplete. You can run this script again later.", logging.WARNING)
            return False
    
    # Repository exists, proceed with update
    log_message("\nChecking for changes...")
    
    # Check for changes
    success, status_output = run_command("git status --porcelain")
    
    if status_output:
        log_message(f"Changes detected:\n{status_output}")
        
        # Stage changes
        success, _ = run_command("git add .")
        if not success:
            log_message("Failed to stage changes.", logging.ERROR)
            return False
            
        # Commit changes
        commit_msg = f"Auto-update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        success, _ = run_command(f'git commit -m "{commit_msg}"')
        if not success:
            log_message("Failed to commit changes.", logging.ERROR)
            return False
            
        log_message("Changes committed successfully.")
    else:
        log_message("No local changes to commit.")
    
    # Try to pull changes
    log_message("\nPulling latest changes from remote...")
    success, pull_output = run_command(f"git pull origin {BRANCH}")
    
    if not success:
        # Handle authentication issues
        if "Authentication failed" in pull_output or "could not read Username" in pull_output:
            log_message("Authentication failed. Please set up credentials.", logging.ERROR)
            
            # Offer GitHub Desktop option
            if use_github_desktop or (not skip_prompt and input("Do you want to use GitHub Desktop for authentication? (y/n): ").lower() == 'y'):
                webbrowser.open(f"github-desktop://openRepository/{REPO_DIR}")
                log_message("GitHub Desktop opening. Please complete authentication there.")
                input("Press Enter when authentication is complete...")
                
                # Try pull again
                success, pull_output = run_command(f"git pull origin {BRANCH}")
                if not success:
                    log_message("Pull still failing. Please resolve authentication manually.", logging.ERROR)
                    return False
            else:
                log_message("Please set up Git credentials manually.", logging.ERROR)
                return False
        else:
            log_message(f"Pull failed: {pull_output}", logging.ERROR)
            return False
    
    # Check for merge conflicts after pull
    if check_for_conflicts():
        log_message("Please resolve conflicts before continuing.", logging.ERROR)
        log_message("After resolving conflicts, commit changes and run this script again.")
        return False
    
    # Push changes if we made a commit
    if status_output:
        log_message("\nPushing changes to remote...")
        success, push_output = run_command(f"git push origin {BRANCH}")
        
        if not success:
            if "Authentication failed" in push_output or "could not read Username" in push_output:
                log_message("Authentication failed for push. Please set up credentials.", logging.ERROR)
                
                # Offer GitHub Desktop option
                if use_github_desktop or (not skip_prompt and input("Do you want to use GitHub Desktop for authentication? (y/n): ").lower() == 'y'):
                    webbrowser.open(f"github-desktop://openRepository/{REPO_DIR}")
                    log_message("GitHub Desktop opening. Please complete authentication there.")
                    input("Press Enter when authentication is complete...")
                    
                    # Try push again
                    success, push_output = run_command(f"git push origin {BRANCH}")
                    if not success:
                        log_message("Push still failing. Please resolve authentication manually.", logging.ERROR)
                        return False
                else:
                    log_message("Please set up Git credentials manually.", logging.ERROR)
                    return False
            else:
                log_message(f"Push failed: {push_output}", logging.ERROR)
                return False
    
    log_message("\n[SUCCESS] Git update completed successfully!")
    return True

def update_repository(repo_path, use_github_desktop=True, skip_prompt=False):
    """Main function to update repository"""
    try:
        logger.info(f"Updating repository at {repo_path}")
        return update_repo(use_github_desktop, skip_prompt)
    except Exception as e:
        logger.error(f"Failed to update repository: {e}", exc_info=True)
        return False

def main():
    """Main entry point with command-line interface"""
    global BRANCH, GITHUB_REPO_URL  # Keep this at the beginning of the function
    
    parser = argparse.ArgumentParser(description="Git Repository Manager for ANITA")
    parser.add_argument("--use-desktop", action="store_true", help="Use GitHub Desktop for authentication")
    parser.add_argument("--no-desktop", action="store_true", help="Don't use GitHub Desktop")
    parser.add_argument("--branch", default=BRANCH, help=f"Branch to use (default: {BRANCH})")
    parser.add_argument("--repo-url", default=GITHUB_REPO_URL, help="Repository URL")
    parser.add_argument("--non-interactive", action="store_true", help="Run without user prompts (use defaults)")
    parser.add_argument("--version", action="version", version="Git Repository Manager v1.0")
    args = parser.parse_args()
    
    # Update globals based on args (remove the global declaration from here)
    if args.branch:
        BRANCH = args.branch
    if args.repo_url:
        GITHUB_REPO_URL = args.repo_url
    
    # Determine GitHub Desktop preference
    use_github_desktop = args.use_desktop or not args.no_desktop
        
    try:
        log_message("Git Repository Manager v1.0")
        log_message(f"Repository directory: {REPO_DIR}")
        log_message(f"Log file: {LOG_FILE}")
        log_message(f"Branch: {BRANCH}")
        log_message("-" * 50)
        
        update_repository(REPO_DIR, use_github_desktop, args.non_interactive)
    except KeyboardInterrupt:
        log_message("\nOperation cancelled by user.", logging.WARNING)
    except Exception as e:
        log_message(f"Unexpected error: {str(e)}", logging.ERROR)
        logger.exception("Unhandled exception")
    finally:
        if not args.non_interactive:
            print("\nPress Enter to close this window...")
            input()

if __name__ == "__main__":
    main()