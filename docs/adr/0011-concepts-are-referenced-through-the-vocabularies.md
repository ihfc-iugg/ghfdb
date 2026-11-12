# ADR 0011 — Concepts are referenced through the vocabularies

**Status:** accepted. It replaces how [ADR 0006](0006-cross-field-rules-are-declared-in-python.md)
and [ADR 0010](0010-each-scheme-criterion-is-declared-once.md) name a concept, and where the
declarations of ADR 0010 live.

## Context

The cross-field rules and the criteria of the quality scheme name vocabulary values. Until now a
declaration named a concept by its local name, the last segment of its URI, as a string under the
field whose vocabulary holds it, such as `"pointSource"` under the conductivity method. Three
problems came of that:

1. A string is not a reference. Nothing but the lookup at run time showed that `"pointSource"` was
   a concept at all, and an editor could not follow it to the vocabulary.
2. The names were turned into the terms a field accepts in four places: the check, the scoring,
   the documentation and the reader of the scored fields. Each had its own lookup and its own
   message when a name was wrong.
3. A group that the vocabulary publishes as a collection was copied into the code. The laboratory
   conductivity methods were a tuple of six names, beside a `laboratory` collection that the
   vocabulary already publishes with those six members, and the two exploration-method domains
   were copies of the collections `borehole-and-mine` and `probe-sensing`. A copy drifts when the
   vocabulary changes.

The modules also reached into one another. The borehole criteria imported groups of concepts from
the probe criteria, the scores imported the domains from the module of the cross-field rules, and
"rule" meant both a cross-field rule and the scoring of a domain (`RuleSet`, `RuleScores`,
`ProbeRules`), which made the declarations hard to find among the machinery that evaluates them.

## Decision

A concept is referenced as an `rdflib.URIRef` through `ghfdb.vocabularies.concepts`. For every field
that has a vocabulary, `concepts.<column name>` is the `rdflib.Namespace` of the field's concept
scheme, built from the packaged field schema alone and never from the network, so
`concepts.tc_method.pointSource` and `concepts.tc_source["insitu-probe"]` are the concepts' URIs. A
column name the schema lacks, or a field without a vocabulary, raises `AttributeError` naming it.
There is no concept class of our own: the `URIRef` of `rdflib` is the reference.

A group of concepts that a vocabulary publishes as a collection is referenced as that collection.
The laboratory conductivity methods are `concepts.tc_method.laboratory`, and the two domains of the
scheme are `concepts.explo_method["borehole-and-mine"]` and
`concepts.explo_method["probe-sensing"]`. A group is replaced by a collection only when the
collection has exactly the same members. The other groups of the scheme, which the vocabularies do
not publish, stay lists of references.

One resolver, `ghfdb.fields.schema.FieldConcepts.resolve`, takes the fields, the references the
declarations name and the vocabularies, and gives for each field the term of every concept it
accepts and the members of every collection named, nested collections included. It refuses a
reference that is neither an allowed value of its field nor a collection of the field's scheme with a
`MissingSchemeError` naming the field and the reference. The check, the scoring and the
documentation all resolve through it, and the scored fields are read as concept URIs.

The declarations come before the code that evaluates them:

* `ghfdb.qc.rules` declares the cross-field rules and nothing else.
* `ghfdb.qc.scheme` declares the quality scheme: the domains, the groups of concepts that more than
  one domain names, the criteria of each domain and the grades.
* `ghfdb.qc.engine` holds how declarations are evaluated: the kinds of rule, the tables and
  penalties, the scored inputs and the scoring of a domain. Nothing outside `ghfdb.qc` imports it,
  except the documentation extensions and the tests.

The scoring of a domain is a `DomainScoring`, so that "rule" means a cross-field rule only.

## Why

A reference is checked by the tools. A misspelt attribute of a namespace is found by reading the
code, and a concept that a vocabulary no longer holds is refused by the resolver naming the field
and the concept. Using the `URIRef` of `rdflib` costs nothing to maintain and is what a reader of the
vocabulary files already knows.

Referencing a published collection means the code cannot disagree with the vocabulary about what
the collection holds. When the vocabulary adds a laboratory method, the scheme scores it as one.

One resolver means one message, one set of rules for a collection and one place to change when the
vocabularies change their shape. A field is named once in a declaration, and the resolver already
refuses a URI that is not an allowed value of the field, so no further check that a reference
belongs to the field it is written under is needed.

Splitting the declarations from the machinery lets a reader open `ghfdb.qc.rules` or
`ghfdb.qc.scheme` and read what the scheme says from the top, and tells a contributor what is public
API and what is not.

## Consequences

* A change of a penalty, a group or a domain is one edit to a declaration, as before. A concept
  that a vocabulary renames is refused by the resolver naming the field and the concept.
* A collection a declaration names stands for its members as the vocabulary publishes them, so a
  concept added to the collection is scored with it. A concept withdrawn from a collection is no
  longer scored with it, and a reference to a concept the field no longer accepts is refused.
* Where a page of the documentation lists the members of a collection, it lists them in the order
  the field lists its terms. The laboratory conductivity methods are therefore listed by their
  terms in alphabetical order, where the copy in the code listed them in a hand-written order.
* A field in which two allowed values share a local name is no longer a problem, because the
  reference is the whole URI.
* The Python names of the scoring classes and of the modules changed, and a user of the Python
  API meets the new ones. The changelog lists them.

## Revisit if

A vocabulary publishes a concept scheme whose concepts do not live under the scheme's identifier,
as the external lithology and age vocabularies do, and a declaration needs to name one of them. The
namespace of that field would then be built from the concepts' real address rather than from the
scheme's identifier.
