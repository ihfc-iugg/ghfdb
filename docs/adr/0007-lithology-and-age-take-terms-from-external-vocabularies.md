# ADR 0007 — Lithology and stratigraphic age take their terms from external vocabularies

**Status:** accepted. It extends [ADR 0003](0003-vocabularies-are-read-from-their-permanent-identifiers.md)
and amends Article XI of `CONSTITUTION.md`.

## Decision

Lithology (`C25`) and stratigraphic age (`C26`) take their terms from the two published
vocabularies that the upload template names for them. Neither is an IHFC vocabulary.

| Field | Concept scheme | Collection | File |
|---|---|---|---|
| `C25` | `http://resource.geosciml.org/classifierScheme/cgi/2016.01/simplelithology` | none, so every concept | `https://geosciml.org/resource/vocabulary/cgi/2016/simplelithology.rdf`, RDF/XML |
| `C26` | `http://resource.geosciml.org/vocabulary/timescale/gts2020` | `http://resource.geosciml.org/classifier/ics/ischart/GeochronologicEras` | `https://vocabs.ardc.edu.au/registry/api/resource/downloads/1211/isc2020.ttl`, Turtle |

- A scheme that is not published as Turtle at its identifier is read from a file named in the
  field's `vocabulary` object: `download` is the address and `downloadFormat` the RDF format, as a
  media type (`text/turtle` or `application/rdf+xml`). The two keys are used only for such a
  scheme. Every IHFC vocabulary is still read from its identifier with `.ttl` added.
- The file is downloaded through the same caching session as every other vocabulary file, and
  parsed in the format the field names. The time scale download carries no `ETag`,
  `Last-Modified` or `Cache-Control`, so the session could not keep it at all. A response with
  none of these headers is now used for a day and downloaded again after that; the headers still
  decide for every file that has them, so the IHFC files are read as before.
- `termForm` gains `localName`. The term is the last path segment of the concept's URI, written
  without square brackets, as the template writes these two fields (`acidic_igneous_material`,
  `LowerCretaceous`).
- The members of a `skos:Collection` include the members of every `skos:Collection` it holds. The
  time scale file groups the geochronologic eras by rank in nested collections, and holds boundary
  and stratotype concepts that are not eras and so are not allowed values.
- Both fields still take several values in a cell, separated by `;`.
- Terms match exactly, as for every other vocabulary field. A name the 2020 chart no longer uses
  (`CambrianSeries3`, `CambrianStage5` and `Ionian` appear in the template) is not an allowed
  value.

## Why

The template lists exactly the 265 concepts of the CGI simple lithology vocabulary for `C25` and
181 terms of the International Chronostratigraphic Chart for `C26`. An earlier
decision left both as free text with a pointer to the classification, because no list was
published for them. Both lists are published by their owners, and a free-text field accepts
misspellings that a workbook check could catch and correct with a suggestion.

ADR 0003 reads a scheme from its identifier with `.ttl` added, and Article XI allowed only IHFC
vocabularies. Neither scheme is published at its identifier as Turtle: the CGI scheme is published
as RDF/XML, and the time scale is published as a download of the chart. Naming the file in the
field is the smallest change that reads them. A new reader for each vocabulary, or a copy of the
terms in this repository, would repeat what ADR 0003 rejected.

## Revisit if

Either owner publishes its scheme as Turtle at the scheme's identifier, which makes `download`
unnecessary for it, or the IHFC Controlled Vocabularies adopt these two lists.
