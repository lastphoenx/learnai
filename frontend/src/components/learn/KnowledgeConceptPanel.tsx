"use client";

import type { TrainerBasiswissenConcept, TrainerBasiswissenSection } from "@/lib/api";

type Props = {
  section: TrainerBasiswissenSection;
};

export function KnowledgeConceptPanel({ section }: Props) {
  const concepts = section.concepts || [];
  const templates = section.cloze_templates || [];
  if (concepts.length === 0 && templates.length === 0) return null;

  return (
    <div className="trainer-basiswissen-panel stack">
      <h4 className="trainer-basiswissen-heading">Fachbegriffe &amp; Merksätze</h4>
      {concepts.length > 0 && (
        <div className="trainer-concept-list">
          {concepts.map((concept) => (
            <ConceptCard key={concept.id} concept={concept} />
          ))}
        </div>
      )}
      {templates.length > 0 && (
        <div className="trainer-cloze-preview">
          <p className="muted trainer-cloze-preview-label">Typische Lückentexte zum Üben:</p>
          <ul>
            {templates.slice(0, 6).map((template) => (
              <li key={template.id}>{template.sentence}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ConceptCard({ concept }: { concept: TrainerBasiswissenConcept }) {
  const terms = (concept.parts || [])
    .map((part) => part.term)
    .filter((term, index, all) => term && all.indexOf(term) === index);

  return (
    <article className="trainer-concept-card">
      <header className="trainer-concept-header">
        <strong>{concept.label}</strong>
        {concept.pattern && <p className="trainer-concept-pattern">{concept.pattern}</p>}
      </header>
      {terms.length > 0 && (
        <p className="trainer-concept-terms muted">
          Begriffe: {terms.join(" · ")}
        </p>
      )}
      {concept.example && <p className="trainer-concept-example">Beispiel: {concept.example}</p>}
      {concept.hint && <p className="trainer-concept-hint">{concept.hint}</p>}
    </article>
  );
}
