#!/bin/bash

# =============================================================================
# Git Branch Manager for A0 Telegram Bot
# =============================================================================
# This script manages Git branches and Docker container operations
# Features:
#   - List and switch between branches
#   - Restart telegram bot container after switching
#   - Merge branches
#   - View status and logs
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Project directory
PROJECT_DIR="/a0/usr/projects/my_a0_telegram"
CONTAINER_NAME="a0-telegram-bot"
SERVICE_NAME="telegram-bot"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "\n${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║         Git Branch Manager - A0 Telegram Bot                 ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}\n"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

show_current_branch() {
    local branch=$(git branch --show-current)
    echo -e "\n${BOLD}Current Branch:${NC} ${GREEN}$branch${NC}"
}

check_uncommitted_changes() {
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        return 0  # Has changes
    else
        return 1  # No changes
    fi
}

stash_if_needed() {
    if check_uncommitted_changes; then
        print_warning "Uncommitted changes detected!"
        echo -e "${YELLOW}Changes:${NC}"
        git status -s
        echo ""
        read -p "Stash changes before switching? (y/n): " stash_choice
        if [[ "$stash_choice" == "y" || "$stash_choice" == "Y" ]]; then
            git stash push -m "Auto-stash before branch switch at $(date +%Y%m%d_%H%M%S)"
            print_status "Changes stashed successfully"
            return 0
        else
            print_warning "Proceeding without stashing (changes may be lost or block switch)"
            return 1
        fi
    fi
    return 2  # No changes needed
}

pop_stash_if_available() {
    if git stash list | grep -q .; then
        echo ""
        read -p "Pop the last stash? (y/n): " pop_choice
        if [[ "$pop_choice" == "y" || "$pop_choice" == "Y" ]]; then
            git stash pop
            print_status "Stash restored"
        fi
    fi
}

restart_container() {
    echo -e "\n${BOLD}Restarting Telegram Bot Container...${NC}"
    
    # Check if docker-compose exists in parent directory
    local compose_dir="/a0"
    
    cd "$compose_dir"
    
    # Stop the container
    print_info "Stopping $SERVICE_NAME..."
    docker compose stop "$SERVICE_NAME" 2>/dev/null || docker-compose stop "$SERVICE_NAME" 2>/dev/null || {
        print_error "Failed to stop container"
        cd "$PROJECT_DIR"
        return 1
    }
    
    # Rebuild if requested
    echo ""
    read -p "Rebuild container before restart? (y/n): " rebuild_choice
    if [[ "$rebuild_choice" == "y" || "$rebuild_choice" == "Y" ]]; then
        print_info "Building $SERVICE_NAME..."
        docker compose build "$SERVICE_NAME" 2>/dev/null || docker-compose build "$SERVICE_NAME" 2>/dev/null || {
            print_error "Failed to build container"
            cd "$PROJECT_DIR"
            return 1
        }
    fi
    
    # Start the container
    print_info "Starting $SERVICE_NAME..."
    docker compose up -d "$SERVICE_NAME" 2>/dev/null || docker-compose up -d "$SERVICE_NAME" 2>/dev/null || {
        print_error "Failed to start container"
        cd "$PROJECT_DIR"
        return 1
    }
    
    cd "$PROJECT_DIR"
    print_status "Container restarted successfully!"
    
    # Show logs option
    echo ""
    read -p "View container logs? (y/n): " logs_choice
    if [[ "$logs_choice" == "y" || "$logs_choice" == "Y" ]]; then
        show_logs
    fi
}

show_logs() {
    echo -e "\n${BOLD}Container Logs (Ctrl+C to exit):${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}\n"
    docker logs -f --tail 50 "$CONTAINER_NAME" 2>/dev/null || {
        print_error "Could not fetch logs"
    }
}

# =============================================================================
# Main Functions
# =============================================================================

list_branches() {
    print_header
    echo -e "${BOLD}Available Branches:${NC}\n"
    
    # Local branches
    echo -e "${CYAN}Local Branches:${NC}"
    git branch --format="%(if)%(HEAD)%(then)* ${GREEN}%(refname:short)${NC} (current)%(else)  %(refname:short)%(end)" 2>/dev/null
    
    echo ""
    
    # Remote branches
    echo -e "${CYAN}Remote Branches:${NC}"
    git branch -r --format="  %(refname:short)" 2>/dev/null | head -20
    
    show_current_branch
    echo ""
}

switch_branch() {
    print_header
    list_branches
    
    echo -e "\nEnter branch name to switch to:"
    read -p "> " target_branch
    
    if [[ -z "$target_branch" ]]; then
        print_error "No branch specified"
        return 1
    fi
    
    # Check if branch exists
    if ! git show-ref --verify --quiet "refs/heads/$target_branch" && \
       ! git show-ref --verify --quiet "refs/remotes/origin/$target_branch"; then
        print_error "Branch '$target_branch' does not exist"
        echo ""
        read -p "Create new branch '$target_branch'? (y/n): " create_choice
        if [[ "$create_choice" == "y" || "$create_choice" == "Y" ]]; then
            git checkout -b "$target_branch"
            print_status "Created and switched to '$target_branch'"
        else
            return 1
        fi
    else
        # Stash if needed
        local stashed=0
        stash_if_needed
        stashed=$?
        
        # Switch branch
        print_info "Switching to '$target_branch'..."
        if git checkout "$target_branch" 2>/dev/null; then
            print_status "Switched to '$target_branch'"
            
            # Pop stash if we stashed
            if [[ $stashed -eq 0 ]]; then
                pop_stash_if_available
            fi
        else
            print_error "Failed to switch to '$target_branch'"
            return 1
        fi
    fi
    
    show_current_branch
    
    # Ask to restart container
    echo ""
    read -p "Restart Telegram Bot container? (y/n): " restart_choice
    if [[ "$restart_choice" == "y" || "$restart_choice" == "Y" ]]; then
        restart_container
    fi
}

merge_branch() {
    print_header
    show_current_branch
    
    echo -e "\n${YELLOW}Merge another branch into current branch${NC}"
    echo -e "${CYAN}Available branches:${NC}"
    git branch --format="  %(refname:short)" | grep -v "^\*"
    
    echo -e "\nEnter branch to merge into $(git branch --show-current):"
    read -p "> " source_branch
    
    if [[ -z "$source_branch" ]]; then
        print_error "No branch specified"
        return 1
    fi
    
    # Check if branch exists
    if ! git show-ref --verify --quiet "refs/heads/$source_branch" && \
       ! git show-ref --verify --quiet "refs/remotes/origin/$source_branch"; then
        print_error "Branch '$source_branch' does not exist"
        return 1
    fi
    
    print_info "Merging '$source_branch' into $(git branch --show-current)..."
    
    if git merge "$source_branch" --no-edit; then
        print_status "Merge successful!"
    else
        print_error "Merge conflict detected!"
        echo -e "\n${YELLOW}Conflicting files:${NC}"
        git diff --name-only --diff-filter=U
        echo -e "\n${YELLOW}Options:${NC}"
        echo "  1. Resolve conflicts manually"
        echo "  2. Abort merge"
        read -p "Choice (1/2): " conflict_choice
        
        if [[ "$conflict_choice" == "2" ]]; then
            git merge --abort
            print_warning "Merge aborted"
        else
            print_info "Please resolve conflicts, then commit"
            echo "After resolving: git add . && git commit"
        fi
        return 1
    fi
    
    # Ask to restart container
    echo ""
    read -p "Restart Telegram Bot container? (y/n): " restart_choice
    if [[ "$restart_choice" == "y" || "$restart_choice" == "Y" ]]; then
        restart_container
    fi
}

create_branch() {
    print_header
    show_current_branch
    
    echo -e "\nEnter new branch name:"
    read -p "> " new_branch
    
    if [[ -z "$new_branch" ]]; then
        print_error "No branch name specified"
        return 1
    fi
    
    # Check if branch already exists
    if git show-ref --verify --quiet "refs/heads/$new_branch"; then
        print_error "Branch '$new_branch' already exists"
        return 1
    fi
    
    print_info "Creating new branch '$new_branch'..."
    git checkout -b "$new_branch"
    print_status "Created and switched to '$new_branch'"
    
    show_current_branch
}

delete_branch() {
    print_header
    show_current_branch
    
    echo -e "\n${YELLOW}Delete a branch${NC}"
    echo -e "${CYAN}Local branches:${NC}"
    git branch --format="  %(refname:short)" | grep -v "$(git branch --show-current)"
    
    echo -e "\nEnter branch to delete:"
    read -p "> " del_branch
    
    if [[ -z "$del_branch" ]]; then
        print_error "No branch specified"
        return 1
    fi
    
    local current=$(git branch --show-current)
    if [[ "$del_branch" == "$current" ]]; then
        print_error "Cannot delete current branch"
        return 1
    fi
    
    read -p "Are you sure you want to delete '$del_branch'? (y/n): " confirm
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        git branch -D "$del_branch" 2>/dev/null || {
            print_error "Could not delete branch (may have unmerged changes)"
            read -p "Force delete? (y/n): " force_del
            if [[ "$force_del" == "y" || "$force_del" == "Y" ]]; then
                git branch -D "$del_branch"
                print_status "Branch '$del_branch' deleted"
            fi
            return 1
        }
        print_status "Branch '$del_branch' deleted"
    fi
}

push_branch() {
    print_header
    show_current_branch
    
    local current=$(git branch --show-current)
    
    print_info "Pushing '$current' to origin..."
    
    # Check if upstream is set
    if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} &>/dev/null; then
        print_warning "No upstream set for '$current'"
        read -p "Push and set upstream? (y/n): " upstream_choice
        if [[ "$upstream_choice" == "y" || "$upstream_choice" == "Y" ]]; then
            git push -u origin "$current"
        else
            return 1
        fi
    else
        git push
    fi
    
    print_status "Push complete"
}

pull_branch() {
    print_header
    show_current_branch
    
    local current=$(git branch --show-current)
    
    # Stash if needed
    stash_if_needed
    
    print_info "Pulling latest changes for '$current'..."
    git pull
    
    print_status "Pull complete"
    
    pop_stash_if_available
}

show_status() {
    print_header
    show_current_branch
    
    echo -e "\n${BOLD}Git Status:${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    git status
    
    echo -e "\n${BOLD}Last 5 Commits:${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    git log --oneline -5
    
    echo -e "\n${BOLD}Container Status:${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

quick_switch() {
    print_header
    echo -e "${BOLD}Quick Switch - Recent Branches${NC}\n"
    
    # Show recent branches
    echo -e "${CYAN}Recent branches:${NC}"
    local branches=$(git for-each-ref --sort=-committerdate --format='%(refname:short)' refs/heads/ | head -10)
    local i=1
    echo "$branches" | while read branch; do
        echo "  $i) $branch"
        ((i++))
    done
    
    echo -e "\nEnter number or branch name:"
    read -p "> " choice
    
    if [[ "$choice" =~ ^[0-9]+$ ]]; then
        target=$(echo "$branches" | sed -n "${choice}p")
    else
        target="$choice"
    fi
    
    if [[ -n "$target" ]]; then
        stash_if_needed
        git checkout "$target" 2>/dev/null && print_status "Switched to '$target'" || print_error "Could not switch"
        pop_stash_if_available
        
        read -p "Restart container? (y/n): " rs
        [[ "$rs" == "y" || "$rs" == "Y" ]] && restart_container
    fi
}

# =============================================================================
# Main Menu
# =============================================================================

main_menu() {
    while true; do
        print_header
        show_current_branch
        
        echo -e "\n${BOLD}Options:${NC}"
        echo -e "  ${GREEN}1)${NC} List branches"
        echo -e "  ${GREEN}2)${NC} Switch branch"
        echo -e "  ${GREEN}3)${NC} Quick switch (recent)"
        echo -e "  ${GREEN}4)${NC} Create new branch"
        echo -e "  ${GREEN}5)${NC} Merge branch"
        echo -e "  ${GREEN}6)${NC} Delete branch"
        echo -e "  ${GREEN}7)${NC} Push current branch"
        echo -e "  ${GREEN}8)${NC} Pull current branch"
        echo -e "  ${YELLOW}R)${NC} Restart Telegram Bot container"
        echo -e "  ${YELLOW}L)${NC} View container logs"
        echo -e "  ${CYAN}S)${NC} Show full status"
        echo -e "  ${RED}Q)${NC} Quit"
        
        echo -e "\nEnter choice:"
        read -p "> " choice
        
        case $choice in
            1) list_branches ;;
            2) switch_branch ;;
            3) quick_switch ;;
            4) create_branch ;;
            5) merge_branch ;;
            6) delete_branch ;;
            7) push_branch ;;
            8) pull_branch ;;
            [Rr]) restart_container ;;
            [Ll]) show_logs ;;
            [Ss]) show_status ;;
            [Qq]) 
                echo -e "\n${GREEN}Goodbye!${NC}\n"
                exit 0 
                ;;
            *) 
                print_error "Invalid option"
                ;;
        esac
        
        echo -e "\n${CYAN}Press Enter to continue...${NC}"
        read -r
    done
}

# =============================================================================
# Entry Point
# =============================================================================

# Check if we're in a git repository
if [[ ! -d ".git" ]]; then
    print_error "Not a git repository!"
    exit 1
fi

# Handle command line arguments
if [[ $# -gt 0 ]]; then
    case "$1" in
        switch|s)
            if [[ -n "$2" ]]; then
                stash_if_needed
                git checkout "$2" && print_status "Switched to '$2'" || print_error "Could not switch"
                pop_stash_if_available
                [[ "$3" == "-r" ]] && restart_container
            else
                switch_branch
            fi
            ;;
        merge|m)
            if [[ -n "$2" ]]; then
                git merge "$2" && print_status "Merged '$2'" || print_error "Merge failed"
                [[ "$3" == "-r" ]] && restart_container
            else
                merge_branch
            fi
            ;;
        restart|r)
            restart_container
            ;;
        logs|l)
            show_logs
            ;;
        status|st)
            show_status
            ;;
        list|ls)
            list_branches
            ;;
        push|p)
            push_branch
            ;;
        pull|pl)
            pull_branch
            ;;
        create|c)
            create_branch
            ;;
        delete|d)
            delete_branch
            ;;
        help|h|--help|-h)
            echo "Usage: $0 [command] [arguments]"
            echo ""
            echo "Commands:"
            echo "  switch <branch> [-r]    Switch to branch (optional: restart after)"
            echo "  merge <branch> [-r]     Merge branch into current (optional: restart after)"
            echo "  restart                 Restart Telegram Bot container"
            echo "  logs                    Show container logs"
            echo "  status                  Show git and container status"
            echo "  list                    List all branches"
            echo "  push                    Push current branch"
            echo "  pull                    Pull current branch"
            echo "  create                  Create new branch"
            echo "  delete                  Delete a branch"
            echo "  help                    Show this help"
            echo ""
            echo "Run without arguments for interactive menu."
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information."
            exit 1
            ;;
    esac
else
    # No arguments - show interactive menu
    main_menu
fi
