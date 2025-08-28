"""
Progress tracking utilities for KOMpass route analysis.
Provides user feedback during long-running operations.
"""

import streamlit as st
from typing import Dict, List, Optional, Callable, Any
import time
from contextlib import contextmanager


class ProgressTracker:
    """Tracks and displays progress for multi-step operations."""
    
    def __init__(self, title: str = "Processing..."):
        """Initialize progress tracker.
        
        Args:
            title: Title to display in the progress indicator
        """
        self.title = title
        self.steps: List[Dict] = []
        self.current_step = 0
        self.start_time = None
        self.progress_bar = None
        self.status_text = None
        
    def add_step(self, name: str, description: str = "", weight: float = 1.0):
        """Add a step to track.
        
        Args:
            name: Step name/identifier
            description: User-friendly description
            weight: Relative weight of this step (for progress calculation)
        """
        self.steps.append({
            'name': name,
            'description': description or name,
            'weight': weight,
            'start_time': None,
            'end_time': None,
            'status': 'pending'  # pending, running, completed, failed
        })
    
    def start(self):
        """Start the progress tracking."""
        self.start_time = time.time()
        self.current_step = 0
        
        # Create Streamlit UI components
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        
        # Update initial display
        self._update_display()
    
    def start_step(self, step_name: str):
        """Mark a step as started.
        
        Args:
            step_name: Name of the step to start
        """
        # Find step by name
        step_index = None
        for i, step in enumerate(self.steps):
            if step['name'] == step_name:
                step_index = i
                break
        
        if step_index is not None:
            self.current_step = step_index
            self.steps[step_index]['status'] = 'running'
            self.steps[step_index]['start_time'] = time.time()
            self._update_display()
    
    def complete_step(self, step_name: str, result: Any = None):
        """Mark a step as completed.
        
        Args:
            step_name: Name of the step to complete
            result: Optional result data from the step
        """
        # Find step by name
        for step in self.steps:
            if step['name'] == step_name:
                step['status'] = 'completed'
                step['end_time'] = time.time()
                step['result'] = result
                break
        
        self._update_display()
    
    def fail_step(self, step_name: str, error: str):
        """Mark a step as failed.
        
        Args:
            step_name: Name of the step that failed
            error: Error message
        """
        # Find step by name
        for step in self.steps:
            if step['name'] == step_name:
                step['status'] = 'failed'
                step['end_time'] = time.time()
                step['error'] = error
                break
        
        self._update_display()
    
    def _update_display(self):
        """Update the progress display."""
        if not self.progress_bar or not self.status_text:
            return
        
        # Calculate overall progress
        total_weight = sum(step['weight'] for step in self.steps)
        completed_weight = sum(
            step['weight'] for step in self.steps 
            if step['status'] == 'completed'
        )
        
        # Add partial progress for current running step
        current_running_weight = 0
        for step in self.steps:
            if step['status'] == 'running':
                # Assume 50% progress for running step
                current_running_weight = step['weight'] * 0.5
                break
        
        progress = (completed_weight + current_running_weight) / max(total_weight, 1)
        progress = min(progress, 1.0)
        
        # Update progress bar (check if still exists)
        if self.progress_bar:
            try:
                self.progress_bar.progress(progress)
            except:
                # Progress bar might have been cleared, skip update
                pass
        
        # Generate status message
        running_step = next((step for step in self.steps if step['status'] == 'running'), None)
        completed_count = sum(1 for step in self.steps if step['status'] == 'completed')
        failed_count = sum(1 for step in self.steps if step['status'] == 'failed')
        
        if running_step:
            elapsed = time.time() - running_step['start_time']
            status_msg = f"**{self.title}** - {running_step['description']} ({elapsed:.1f}s)"
        elif failed_count > 0:
            status_msg = f"**{self.title}** - ❌ {failed_count} step(s) failed"
        elif completed_count == len(self.steps):
            total_time = time.time() - self.start_time if self.start_time else 0
            status_msg = f"**{self.title}** - ✅ Completed in {total_time:.1f}s"
        else:
            status_msg = f"**{self.title}** - {completed_count}/{len(self.steps)} steps completed"
        
        # Show step-by-step status
        step_status = []
        for i, step in enumerate(self.steps):
            if step['status'] == 'completed':
                icon = "✅"
            elif step['status'] == 'running':
                icon = "🔄"
            elif step['status'] == 'failed':
                icon = "❌"
            else:
                icon = "⏳"
            
            step_status.append(f"{icon} {step['description']}")
        
        # Update status display (check if still exists)
        if self.status_text:
            try:
                status_display = f"{status_msg}\n\n" + "\n".join(step_status)
                self.status_text.markdown(status_display)
            except:
                # Status text might have been cleared, skip update
                pass
    
    def finish(self):
        """Clean up progress tracking."""
        total_time = time.time() - self.start_time if self.start_time else 0
        failed_steps = [step for step in self.steps if step['status'] == 'failed']
        
        # Complete the progress bar to 100%
        if self.progress_bar:
            try:
                self.progress_bar.progress(1.0)
            except:
                # Progress bar might have been cleared already
                pass
        
        # Show final status message
        if failed_steps:
            if self.status_text:
                try:
                    self.status_text.error(f"❌ Process completed with {len(failed_steps)} error(s) in {total_time:.1f}s")
                except:
                    # Status text might have been cleared already
                    pass
        else:
            if self.status_text:
                try:
                    self.status_text.success(f"✅ {self.title} completed successfully in {total_time:.1f}s")
                except:
                    # Status text might have been cleared already
                    pass
        
        # Clear only the progress bar to prevent accumulation, but keep the final status message
        if self.progress_bar:
            try:
                self.progress_bar.empty()
            except:
                # Progress bar might have been cleared already
                pass
            finally:
                self.progress_bar = None
    
    def _clear_ui_elements(self):
        """Clear all UI elements completely."""
        if self.progress_bar:
            self.progress_bar.empty()
            self.progress_bar = None
        if self.status_text:
            self.status_text.empty()
            self.status_text = None
    
    @contextmanager
    def track_step(self, step_name: str):
        """Context manager for tracking a step.
        
        Args:
            step_name: Name of the step to track
        
        Usage:
            with tracker.track_step('analyze_gradients'):
                result = analyze_gradients(data)
        """
        self.start_step(step_name)
        try:
            yield
            self.complete_step(step_name)
        except Exception as e:
            self.fail_step(step_name, str(e))
            raise


def create_route_analysis_tracker() -> ProgressTracker:
    """Create a pre-configured progress tracker for route analysis."""
    tracker = ProgressTracker("Route Analysis")
    
    # Add all the analysis steps
    tracker.add_step("parse_data", "📄 Parsing route data", weight=1.0)
    tracker.add_step("basic_stats", "📊 Calculating basic statistics", weight=1.0)
    tracker.add_step("gradients", "⛰️ Analyzing gradients and elevation", weight=2.0)
    tracker.add_step("climbs", "🚵 Identifying climbing segments", weight=2.0)
    tracker.add_step("complexity", "🗺️ Analyzing route complexity", weight=1.5)
    tracker.add_step("terrain", "🏔️ Classifying terrain type", weight=1.0)
    tracker.add_step("power", "⚡ Estimating power requirements", weight=1.5)
    tracker.add_step("ml_features", "🤖 Generating ML features", weight=1.0)
    
    return tracker


def create_traffic_analysis_tracker() -> ProgressTracker:
    """Create a progress tracker specifically for traffic analysis."""
    tracker = ProgressTracker("Traffic Analysis")
    
    tracker.add_step("bounds_check", "🗺️ Checking route bounds", weight=0.5)
    tracker.add_step("fetch_infrastructure", "🚦 Fetching traffic infrastructure data", weight=3.0)
    tracker.add_step("find_intersections", "🔍 Finding route intersections", weight=2.0)
    tracker.add_step("calculate_metrics", "📊 Calculating traffic metrics", weight=1.0)
    tracker.add_step("remove_duplicates", "🧹 Removing duplicate stops", weight=0.5)
    
    return tracker