import os
import subprocess
import sys
import time
import datetime
import logging
import webbrowser

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))  # Parent directory
LOG_FILE = os.path.join(SCRIPT_DIR, 'gitupdate.log')
GITHUB_REPO_URL = "https://github.com/yourusername/your-repo"  # CHANGE THIS
BRANCH = 'main'

# Set up logging
logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Add console handler to see logs while running
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger().addHandler(console_handler)

def log_message(message, level=logging.INFO):
    """Log a message both to file and console"""
    logging.log(level, message)
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
    
    return True

def config_user():
    """Configure Git user details if not already set"""
    # Check if user details are already configured
    success, name = run_command("git config --get user.name", show_output=False)
    if not success or not name:
        name = input("Enter your Git username: ")
        run_command(f'git config --global user.name "{name}"')
        
    success, email = run_command("git config --get user.email", show_output=False)
    if not success or not email:
        email = input("Enter your Git email: ")
        run_command(f'git config --global user.email "{email}"')
        
    log_message("Git user configured.")

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

def update_repo():
    """Update the Git repository"""
    log_message("\n" + "="*50)
    log_message("Starting Git update process...")
    log_message("="*50)
    
    # First, check if this is a Git repository
    if not is_git_repo():
        log_message("This directory is not a Git repository.", logging.WARNING)
        
        # Ask to initialize
        response = input("Do you want to initialize a Git repository here? (y/n): ")
        if response.lower() != 'y':
            log_message("Aborting update.")
            return False
            
        # Initialize repository
        if not init_git_repo():
            return False
            
        # Set up remote
        if not setup_remote():
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
            response = input("Do you want to use GitHub Desktop for authentication? (y/n): ")
            if response.lower() == 'y':
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
    
    # Push changes if we made a commit
    if status_output:
        log_message("\nPushing changes to remote...")
        success, push_output = run_command(f"git push origin {BRANCH}")
        
        if not success:
            if "Authentication failed" in push_output or "could not read Username" in push_output:
                log_message("Authentication failed for push. Please set up credentials.", logging.ERROR)
                
                # Offer GitHub Desktop option
                response = input("Do you want to use GitHub Desktop for authentication? (y/n): ")
                if response.lower() == 'y':
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
    
    log_message("\n✅ Git update completed successfully!")
    return True

if __name__ == "__main__":
    print(f"Git Auto-Update Tool")
    print(f"Repository directory: {REPO_DIR}")
    print(f"Log file: {LOG_FILE}")
    print("-" * 50)
    
    success = update_repo()
    
    if success:
        print("\n✅ Update completed successfully!")
    else:
        print("\n❌ Update failed. See log for details.")
    
    # Always keep window open at the end
    print("\nPress Enter to close this window...")
    input()