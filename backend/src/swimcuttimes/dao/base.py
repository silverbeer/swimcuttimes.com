"""Base DAO with Supabase client connection."""

import os
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from supabase import Client, create_client

T = TypeVar("T", bound=BaseModel)


class SupabaseClient:
    """Singleton Supabase client manager."""

    _instance: Client | None = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create the Supabase client."""
        if cls._instance is None:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")

            if not url or not key:
                raise RuntimeError(
                    "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
                )

            cls._instance = create_client(url, key)

        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the client (useful for testing)."""
        cls._instance = None


class BaseDAO(Generic[T]):
    """Base Data Access Object with common CRUD operations."""

    table_name: str
    model_class: type[T]

    def __init__(self, client: Client | None = None):
        """Initialize the DAO.

        Args:
            client: Supabase client. If not provided, uses the singleton.
        """
        self.client = client or SupabaseClient.get_client()

    @property
    def table(self):
        """Get the table reference."""
        return self.client.table(self.table_name)

    def get_by_id(self, id: UUID) -> T | None:
        """Get a single record by ID.

        Args:
            id: The record's UUID

        Returns:
            The model instance or None if not found
        """
        result = self.table.select("*").eq("id", str(id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all records with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        result = self.table.select("*").range(offset, offset + limit - 1).execute()
        return [self._to_model(row) for row in result.data]

    def create(self, model: T) -> T:
        """Create a new record.

        Args:
            model: The model instance to create

        Returns:
            The created model with ID populated
        """
        data = self._to_db(model)
        result = self.table.insert(data).execute()
        return self._to_model(result.data[0])

    def update(self, id: UUID, model: T) -> T | None:
        """Update an existing record.

        Args:
            id: The record's UUID
            model: The model with updated values

        Returns:
            The updated model or None if not found
        """
        data = self._to_db(model)
        result = self.table.update(data).eq("id", str(id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def delete(self, id: UUID) -> bool:
        """Delete a record by ID.

        Args:
            id: The record's UUID

        Returns:
            True if deleted, False if not found
        """
        result = self.table.delete().eq("id", str(id)).execute()
        return len(result.data) > 0

    def count(self) -> int:
        """Get total count of records.

        Returns:
            Total number of records in the table
        """
        result = self.table.select("*", count="exact").execute()
        return result.count or 0

    def _to_model(self, row: dict) -> T:
        """Convert a database row to a model instance.

        Override this method for custom mapping logic.
        """
        return self.model_class(**row)

    def _to_db(self, model: T) -> dict:
        """Convert a model instance to a database row.

        Override this method for custom mapping logic.
        """
        data = model.model_dump(exclude_none=True)

        # Convert UUIDs to strings
        for key, value in data.items():
            if isinstance(value, UUID):
                data[key] = str(value)

        return data
