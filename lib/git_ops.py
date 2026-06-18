import os
import subprocess
import logging
from typing import Tuple

def get_commit_url(commit_hash: str) -> str:
    """
    Dynamically resolve the GitHub URL for a given commit hash using the remote origin.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_url = f"https://github.com/vib3withsimran/The-war-room/commit/{commit_hash}"
    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_root, capture_output=True, text=True)
        if res.returncode == 0:
            url = res.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            if url.startswith("git@github.com:"):
                url = url.replace("git@github.com:", "https://github.com/")
            return f"{url}/commit/{commit_hash}"
    except Exception:
        pass
    return default_url

def commit_postmortem(incident_id: str, markdown_content: str) -> Tuple[bool, str]:
    """
    Writes a postmortem report to postmortems/inc-{incident_id}/postmortem.md
    and attempts to commit it to Git.
    Returns (success, commit_hash). If git was not available or not committed, commit_hash is empty.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dir_name = incident_id if incident_id.startswith("inc-") else f"inc-{incident_id}"
    postmortems_dir = os.path.join(repo_root, "postmortems", dir_name)
    
    # Ensure directory exists
    os.makedirs(postmortems_dir, exist_ok=True)
    postmortem_path = os.path.join(postmortems_dir, "postmortem.md")
    
    # Write the file
    try:
        with open(postmortem_path, "w") as f:
            f.write(markdown_content)
        logging.info(f"Written postmortem file to {postmortem_path}")
    except Exception as e:
        logging.error(f"Failed to write postmortem file: {e}")
        return False, ""
        
    # Check if git is available and it's a repository
    try:
        # Check git status
        res = subprocess.run(["git", "status"], cwd=repo_root, capture_output=True, text=True)
        if res.returncode != 0:
            logging.warning("Not a git repository or git not available. Fallback to writing file only.")
            return True, ""
            
        # Git add
        rel_dir = os.path.join("postmortems", dir_name)
        res_add = subprocess.run(["git", "add", rel_dir], cwd=repo_root, capture_output=True, text=True)
        if res_add.returncode != 0:
            logging.error(f"git add failed: {res_add.stderr}")
            return False, ""
            
        # Git commit
        commit_msg = f"docs: postmortem inc-{incident_id}"
        res_commit = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_root, capture_output=True, text=True)
        if res_commit.returncode != 0:
            if "nothing to commit" in res_commit.stdout or "nothing to commit" in res_commit.stderr or "no changes added to commit" in res_commit.stdout:
                logging.info("Nothing to commit (postmortem unchanged).")
                # Return last commit hash
                res_hash = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, capture_output=True, text=True)
                return True, res_hash.stdout.strip()
            logging.error(f"git commit failed: {res_commit.stderr}")
            return False, ""
            
        # Get commit hash
        res_hash = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, capture_output=True, text=True)
        commit_hash = res_hash.stdout.strip()
        logging.info(f"Successfully committed postmortem. Commit hash: [{commit_hash}]")
        return True, commit_hash
        
    except Exception as e:
        logging.warning(f"Git execution failed: {e}. Fallback to writing file only.")
        return True, ""
