"""Project discovery module for A0 Telegram bot.

Dynamically discovers available A0 projects from the projects directory.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """Represents an A0 project."""
    name: str  # Folder name
    title: str  # Human-readable title
    description: str  # Project description
    path: str  # Full path to project folder
    
    def __str__(self) -> str:
        return f"{self.title} ({self.name})"


class ProjectDiscovery:
    """Discovers and manages A0 projects."""
    
    def __init__(self, projects_path: str = "/a0/usr/projects"):
        self.projects_path = projects_path
        self._projects: Optional[List[Project]] = None
    
    def discover_projects(self) -> List[Project]:
        """Discover all available projects from the projects directory."""
        projects = []
        
        if not os.path.exists(self.projects_path):
            logger.warning(f"Projects path does not exist: {self.projects_path}")
            return projects
        
        for folder_name in os.listdir(self.projects_path):
            folder_path = os.path.join(self.projects_path, folder_name)
            
            # Skip non-directories
            if not os.path.isdir(folder_path):
                continue
            
            # Check for .a0proj/project.json
            project_json_path = os.path.join(folder_path, ".a0proj", "project.json")
            
            if os.path.exists(project_json_path):
                try:
                    with open(project_json_path, "r") as f:
                        data = json.load(f)
                    
                    project = Project(
                        name=folder_name,
                        title=data.get("title", folder_name),
                        description=data.get("description", ""),
                        path=folder_path
                    )
                    projects.append(project)
                    logger.debug(f"Discovered project: {project.name} - {project.title}")
                except Exception as e:
                    logger.warning(f"Failed to read project {folder_name}: {e}")
            else:
                # Folder without .a0proj - still include as a basic project
                project = Project(
                    name=folder_name,
                    title=folder_name,
                    description="",
                    path=folder_path
                )
                projects.append(project)
                logger.debug(f"Found folder without .a0proj: {folder_name}")
        
        # Sort by name
        projects.sort(key=lambda p: p.name.lower())
        self._projects = projects
        return projects
    
    def get_projects(self, refresh: bool = False) -> List[Project]:
        """Get cached projects or refresh if needed."""
        if self._projects is None or refresh:
            return self.discover_projects()
        return self._projects
    
    def get_project_by_name(self, name: str) -> Optional[Project]:
        """Get a project by its folder name."""
        for project in self.get_projects():
            if project.name == name:
                return project
        return None
    
    def get_project_names(self) -> List[str]:
        """Get list of project folder names."""
        return [p.name for p in self.get_projects()]
    
    def format_project_list(self, current_project: Optional[str] = None) -> str:
        """Format project list for display in Telegram."""
        projects = self.get_projects()
        
        if not projects:
            return "📁 No projects found."
        
        lines = ["📁 *Available Projects:\\n"]
        
        for project in projects:
            marker = "✅ " if project.name == current_project else "• "
            title = project.title or project.name
            
            if project.description:
                lines.append(f"{marker}`{project.name}` - {title}\\n   _{project.description[:50]}..._\\n")
            else:
                lines.append(f"{marker}`{project.name}` - {title}\\n")
        
        return "\n".join(lines)


# Global instance
_project_discovery: Optional[ProjectDiscovery] = None


def get_project_discovery(projects_path: str = "/a0/usr/projects") -> ProjectDiscovery:
    """Get the global project discovery instance."""
    global _project_discovery
    if _project_discovery is None:
        _project_discovery = ProjectDiscovery(projects_path)
    return _project_discovery
