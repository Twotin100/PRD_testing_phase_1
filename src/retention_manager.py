"""
Retention and versioning manager for crawl data.

Implements:
- 18-month data retention policy
- 6-month re-crawl scheduling
- Maximum 3 versions per business
- Automatic cleanup of expired data

This module manages the lifecycle of crawl data from creation to expiration.
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from crawl_config import get_retention_config, RetentionConfig


class RetentionManager:
    """
    Manages crawl data retention and versioning.

    Retention Policy:
    - Each crawl is kept for 18 months from crawl date
    - Maximum 3 versions (crawls) per business
    - Re-crawl due every 6 months
    - Oldest versions deleted when exceeding max versions
    """

    def __init__(
        self,
        storage_dir: str = "crawl_storage",
        config: Optional[RetentionConfig] = None,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.config = config or get_retention_config()

        # Index file tracks all crawls
        self.index_file = self.storage_dir / "crawl_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load the crawl index from disk."""
        if self.index_file.exists():
            with open(self.index_file, "r") as f:
                return json.load(f)
        return {
            "businesses": {},  # business_url -> business metadata
            "crawls": {},      # crawl_id -> crawl metadata
            "last_cleanup": None,
        }

    def _save_index(self) -> None:
        """Save the crawl index to disk."""
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2, default=str)

    def register_business(
        self,
        business_url: str,
        business_type: str,
        business_name: Optional[str] = None,
    ) -> str:
        """
        Register a new business or get existing registration.

        Returns:
            Business ID (normalized URL)
        """
        # Normalize URL as business ID
        business_id = self._normalize_url(business_url)

        if business_id not in self.index["businesses"]:
            self.index["businesses"][business_id] = {
                "business_url": business_url,
                "business_type": business_type,
                "business_name": business_name,
                "crawl_ids": [],
                "first_crawled_at": None,
                "last_crawled_at": None,
                "next_crawl_due": None,
                "crawl_count": 0,
            }
            self._save_index()

        return business_id

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to use as business identifier."""
        # Remove protocol and trailing slash
        url = url.lower()
        for prefix in ["https://", "http://", "www."]:
            if url.startswith(prefix):
                url = url[len(prefix):]
        return url.rstrip("/")

    def register_crawl(
        self,
        crawl_id: str,
        business_url: str,
        business_type: str,
        crawl_file_path: str,
        pages_crawled: int,
        credits_used: int,
    ) -> Dict[str, Any]:
        """
        Register a completed crawl.

        This:
        1. Associates crawl with business
        2. Sets expiration date (18 months)
        3. Calculates next re-crawl date (6 months)
        4. Enforces max versions (3) by deleting oldest if needed

        Returns:
            Crawl metadata including version number
        """
        business_id = self.register_business(business_url, business_type)
        business = self.index["businesses"][business_id]

        now = datetime.utcnow()

        # Calculate version number
        version = business["crawl_count"] + 1

        # Create crawl record
        crawl_record = {
            "crawl_id": crawl_id,
            "business_id": business_id,
            "business_url": business_url,
            "business_type": business_type,
            "version": version,
            "crawl_file": crawl_file_path,
            "pages_crawled": pages_crawled,
            "credits_used": credits_used,
            "crawled_at": now.isoformat(),
            "expires_at": (now + self.config.retention_period).isoformat(),
        }

        # Add to index
        self.index["crawls"][crawl_id] = crawl_record

        # Update business record
        business["crawl_ids"].append(crawl_id)
        business["crawl_count"] = version
        business["last_crawled_at"] = now.isoformat()
        business["next_crawl_due"] = (now + self.config.recrawl_interval).isoformat()

        if business["first_crawled_at"] is None:
            business["first_crawled_at"] = now.isoformat()

        # Enforce max versions
        self._enforce_max_versions(business_id)

        self._save_index()

        return crawl_record

    def _enforce_max_versions(self, business_id: str) -> List[str]:
        """
        Ensure business doesn't exceed max versions.

        Deletes oldest crawls if needed.

        Returns:
            List of deleted crawl IDs
        """
        business = self.index["businesses"].get(business_id)
        if not business:
            return []

        deleted = []
        while len(business["crawl_ids"]) > self.config.max_versions_per_business:
            oldest_crawl_id = business["crawl_ids"].pop(0)
            self._delete_crawl(oldest_crawl_id)
            deleted.append(oldest_crawl_id)

        return deleted

    def _delete_crawl(self, crawl_id: str) -> bool:
        """Delete a crawl record and its associated files."""
        crawl = self.index["crawls"].get(crawl_id)
        if not crawl:
            return False

        # Delete the crawl file
        crawl_file = Path(crawl.get("crawl_file", ""))
        if crawl_file.exists():
            crawl_file.unlink()

        # Remove from index
        del self.index["crawls"][crawl_id]

        return True

    def get_businesses_due_for_crawl(self) -> List[Dict[str, Any]]:
        """
        Get list of businesses due for re-crawling.

        A business is due if:
        - Never crawled, OR
        - next_crawl_due is in the past

        Returns:
            List of business records due for crawling
        """
        now = datetime.utcnow()
        due = []

        for business_id, business in self.index["businesses"].items():
            if business["next_crawl_due"] is None:
                # Never crawled
                due.append(business)
            else:
                next_due = datetime.fromisoformat(business["next_crawl_due"])
                if next_due <= now:
                    due.append(business)

        # Sort by longest overdue first
        due.sort(key=lambda b: b.get("next_crawl_due") or "0000-00-00")

        return due

    def cleanup_expired_crawls(self) -> Dict[str, Any]:
        """
        Remove crawls that have exceeded the retention period.

        Returns:
            Summary of cleanup operation
        """
        now = datetime.utcnow()
        expired_crawls = []
        deleted_files = 0
        bytes_freed = 0

        for crawl_id, crawl in list(self.index["crawls"].items()):
            expires_at = datetime.fromisoformat(crawl["expires_at"])
            if expires_at <= now:
                expired_crawls.append(crawl_id)

                # Get file size before deletion
                crawl_file = Path(crawl.get("crawl_file", ""))
                if crawl_file.exists():
                    bytes_freed += crawl_file.stat().st_size

                # Delete crawl
                self._delete_crawl(crawl_id)

                # Remove from business's crawl list
                business_id = crawl.get("business_id")
                if business_id and business_id in self.index["businesses"]:
                    business = self.index["businesses"][business_id]
                    if crawl_id in business["crawl_ids"]:
                        business["crawl_ids"].remove(crawl_id)

                deleted_files += 1

        self.index["last_cleanup"] = now.isoformat()
        self._save_index()

        return {
            "crawls_deleted": len(expired_crawls),
            "files_deleted": deleted_files,
            "bytes_freed": bytes_freed,
            "mb_freed": round(bytes_freed / (1024 * 1024), 2),
            "cleanup_timestamp": now.isoformat(),
        }

    def get_crawl_history(self, business_url: str) -> List[Dict[str, Any]]:
        """Get all crawl records for a business."""
        business_id = self._normalize_url(business_url)
        business = self.index["businesses"].get(business_id)

        if not business:
            return []

        history = []
        for crawl_id in business["crawl_ids"]:
            crawl = self.index["crawls"].get(crawl_id)
            if crawl:
                history.append(crawl)

        return history

    def get_latest_crawl(self, business_url: str) -> Optional[Dict[str, Any]]:
        """Get the most recent crawl for a business."""
        history = self.get_crawl_history(business_url)
        return history[-1] if history else None

    def get_retention_stats(self) -> Dict[str, Any]:
        """Get overall retention statistics."""
        now = datetime.utcnow()

        total_crawls = len(self.index["crawls"])
        total_businesses = len(self.index["businesses"])

        # Count by status
        active_crawls = 0
        expiring_soon = 0  # Within 30 days

        for crawl in self.index["crawls"].values():
            expires_at = datetime.fromisoformat(crawl["expires_at"])
            if expires_at > now:
                active_crawls += 1
                if expires_at <= now + timedelta(days=30):
                    expiring_soon += 1

        # Count businesses due for crawl
        due_for_crawl = len(self.get_businesses_due_for_crawl())

        # Calculate total storage used
        total_size = 0
        for crawl in self.index["crawls"].values():
            crawl_file = Path(crawl.get("crawl_file", ""))
            if crawl_file.exists():
                total_size += crawl_file.stat().st_size

        return {
            "total_businesses": total_businesses,
            "total_crawls": total_crawls,
            "active_crawls": active_crawls,
            "expiring_soon_30d": expiring_soon,
            "businesses_due_for_crawl": due_for_crawl,
            "storage_used_mb": round(total_size / (1024 * 1024), 2),
            "retention_period_days": self.config.retention_period.days,
            "recrawl_interval_days": self.config.recrawl_interval.days,
            "max_versions_per_business": self.config.max_versions_per_business,
            "last_cleanup": self.index.get("last_cleanup"),
        }

    def schedule_recrawl(self, business_url: str, priority: bool = False) -> Optional[datetime]:
        """
        Manually schedule a re-crawl for a business.

        Args:
            business_url: URL of the business
            priority: If True, schedule for immediate crawl

        Returns:
            New next_crawl_due date, or None if business not found
        """
        business_id = self._normalize_url(business_url)
        business = self.index["businesses"].get(business_id)

        if not business:
            return None

        if priority:
            # Schedule for now
            new_due = datetime.utcnow()
        else:
            # Schedule for 6 months from last crawl
            last_crawled = datetime.fromisoformat(business["last_crawled_at"])
            new_due = last_crawled + self.config.recrawl_interval

        business["next_crawl_due"] = new_due.isoformat()
        self._save_index()

        return new_due


def print_retention_report(manager: RetentionManager) -> None:
    """Print a formatted retention report."""
    stats = manager.get_retention_stats()

    print("\n" + "=" * 60)
    print("CRAWL RETENTION REPORT")
    print("=" * 60)
    print(f"""
Policy Settings:
  Retention Period:     {stats['retention_period_days']} days (18 months)
  Re-crawl Interval:    {stats['recrawl_interval_days']} days (6 months)
  Max Versions:         {stats['max_versions_per_business']} per business

Current Status:
  Total Businesses:     {stats['total_businesses']}
  Total Crawls:         {stats['total_crawls']}
  Active Crawls:        {stats['active_crawls']}
  Expiring (30 days):   {stats['expiring_soon_30d']}
  Due for Re-crawl:     {stats['businesses_due_for_crawl']}

Storage:
  Total Used:           {stats['storage_used_mb']} MB

Maintenance:
  Last Cleanup:         {stats['last_cleanup'] or 'Never'}
""")
    print("=" * 60)


if __name__ == "__main__":
    # Example usage and testing
    import tempfile

    # Create a temporary storage directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RetentionManager(storage_dir=tmpdir)

        # Register some test businesses
        print("Registering test businesses...")
        manager.register_business(
            "https://example-kennels.co.uk",
            "dog_kennel",
            "Example Kennels"
        )
        manager.register_business(
            "https://happy-paws.co.uk",
            "dog_groomer",
            "Happy Paws Grooming"
        )

        # Simulate some crawls
        print("\nSimulating crawls...")

        # Create dummy crawl files
        for i, (url, btype) in enumerate([
            ("https://example-kennels.co.uk", "dog_kennel"),
            ("https://example-kennels.co.uk", "dog_kennel"),  # Second version
            ("https://happy-paws.co.uk", "dog_groomer"),
        ]):
            crawl_file = Path(tmpdir) / f"crawl_{i}.json"
            crawl_file.write_text('{"test": "data"}')

            manager.register_crawl(
                crawl_id=f"crawl-{i}",
                business_url=url,
                business_type=btype,
                crawl_file_path=str(crawl_file),
                pages_crawled=10 + i,
                credits_used=50 + i * 10,
            )

        # Print report
        print_retention_report(manager)

        # Test getting crawl history
        print("\nCrawl history for example-kennels.co.uk:")
        history = manager.get_crawl_history("https://example-kennels.co.uk")
        for crawl in history:
            print(f"  Version {crawl['version']}: {crawl['pages_crawled']} pages, expires {crawl['expires_at'][:10]}")

        # Test getting businesses due for crawl
        print("\nBusinesses due for crawl:")
        due = manager.get_businesses_due_for_crawl()
        for business in due:
            print(f"  {business['business_url']} (last: {business['last_crawled_at'][:10] if business['last_crawled_at'] else 'never'})")
