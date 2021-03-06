"""A session connecting to a backend which stores the CUDS in triples."""

import uuid
import rdflib
from osp.core.utils import create_from_triples
from osp.core.utils import iri_from_uid, uid_from_iri, CUDS_IRI_PREFIX
from osp.core.session.db.db_wrapper_session import DbWrapperSession
from abc import abstractmethod


class TripleStoreWrapperSession(DbWrapperSession):
    """A session connecting to a backend which stores the CUDS in triples."""

    # OVERRIDE
    def _apply_added(self, root_obj, buffer):
        # Perform the SQL-Statements to add the elements
        # in the buffers to the DB.

        for added in buffer.values():
            triples = self._substitute_root_iri(added.get_triples())
            self._add(*triples)

    # OVERRIDE
    def _apply_updated(self, root_obj, buffer):
        # Perform the SQL-Statements to update the elements
        # in the buffers in the DB.
        for updated in buffer.values():
            pattern = (updated.iri, None, None)
            self._remove(next(self._substitute_root_iri([pattern])))
            triples = self._substitute_root_iri(updated.get_triples())
            self._add(*triples)

    # OVERRIDE
    def _apply_deleted(self, root_obj, buffer):
        # Perform the SQL-Statements to delete the elements
        # in the buffers in the DB.
        for deleted in buffer.values():
            pattern = (deleted.iri, None, None)
            self._remove(next(self._substitute_root_iri([pattern])))

    # OVERRIDE
    def _load_from_backend(self, uids, expired=None):
        for uid in uids:
            iri = iri_from_uid(uid)
            yield self._load_by_iri(iri)

    # OVERRIDE
    def _load_first_level(self):
        triple = (iri_from_uid(self.root), None, None)
        triple = next(self._substitute_root_iri([triple]))
        iris = {
            o for s, p, o in self._triples(triple)
            if isinstance(o, rdflib.URIRef)
            and str(o).startswith(CUDS_IRI_PREFIX)
            and uid_from_iri(o) != uuid.UUID(int=0)
        }
        iris.add(iri_from_uid(self.root))
        for iri in iris:
            self._load_by_iri(iri)

    # OVERRIDE
    def _load_by_oclass(self, oclass):
        uids = {
            uid_from_iri(s)
            for s, _, _ in self._triples((None, rdflib.RDF.type, oclass.iri))
        }
        uids = {x if x != uuid.UUID(int=0) else self. root for x in uids}
        yield from self._load_from_backend(uids)

    def _substitute_root_iri(self, triples):
        from osp.core.utils import CUDS_IRI_PREFIX
        for triple in triples:
            yield tuple(iri_from_uid(uuid.UUID(int=0))
                        if x is not None and x.startswith(CUDS_IRI_PREFIX)
                        and uid_from_iri(x) == self.root else x
                        for x in triple)

    def _substitute_zero_iri(self, triples):
        from osp.core.utils import CUDS_IRI_PREFIX
        for triple in triples:
            yield tuple(iri_from_uid(self.root)
                        if x is not None and x.startswith(CUDS_IRI_PREFIX)
                        and uid_from_iri(x) == uuid.UUID(int=0) else x
                        for x in triple)

    def _load_by_iri(self, iri):
        """Load the CUDS object wit the given IRI.

        Args:
            iri (rdflib.IRI): The IRI of the CUDS object to oad.

        Returns:
            Cuds - The CUDS object with the given IRI.
        """
        if iri == iri_from_uid(self.root):
            iri = iri_from_uid(uuid.UUID(int=0))
        triples, neighbor_triples = self._load_triples_for_iri(iri)

        triples = self._substitute_zero_iri(triples)
        neighbor_triples = self._substitute_zero_iri(neighbor_triples)

        return create_from_triples(
            triples=triples,
            neighbor_triples=neighbor_triples,
            session=self,
            fix_neighbors=False
        )

    @abstractmethod
    def _triples(self, pattern):
        """Get all triples that match the given pattern.

        Args:
            pattern (Tuple): A triple consisting of subject, predicate, object.
                Each can be None.
        """

    @abstractmethod
    def _add(self, *triples):
        """Add the triple to the database.

        Args:
            triples (Tuple): A tuple consisting of subject, predicate, object.
        """

    @abstractmethod
    def _remove(self, pattern):
        """Remove the triple from the database.

        Args:
            pattern (Tuple): A triple consisting of subject, predicate, object.
                Each can be None.
        """

    @abstractmethod
    def _load_triples_for_iri(self, iri):
        """Load the all triples for the CUDS object with the given IRI.

        Args:
            iri (Tuple): The IRI of the CUDS object to load the triples for.
        """
