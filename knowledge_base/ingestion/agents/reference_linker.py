from knowledge_base.models.entry import KnowledgeEntry


class ReferenceLinker:
    def link(self, entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        tag_index: dict[str, list[str]] = {}
        for entry in entries:
            for tag in entry.tags:
                tag_index.setdefault(tag, []).append(entry.id)

        for entry in entries:
            refs: set[str] = set()
            for tag in entry.tags:
                for eid in tag_index.get(tag, []):
                    if eid != entry.id:
                        refs.add(eid)
            entry.references = list(refs)

        id_map = {e.id: e for e in entries}
        for entry in entries:
            for ref_id in entry.references:
                if ref_id in id_map and entry.id not in id_map[ref_id].referenced_by:
                    id_map[ref_id].referenced_by.append(entry.id)

        return entries
