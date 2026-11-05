# Cross-field rules

The field schema checks each field on its own. A cross-field rule relates several fields of
the same child, such as "a child explored by drilling has its interval bottom filled".
`ghfdb check` applies every rule below after the field check and reports each broken rule as a
`rule` problem, with the rule's identifier linked to its entry on this page. The rules are
declared in `ghfdb.qc.rules`, and this page is built from them, so it cannot disagree with the
check.

## The two kinds of rule

* **Required for a domain.** A child whose exploration method belongs to a domain has every
  field that is mandatory for that domain only filled. The fields are read from the field
  schema.
* **Allowed when.** When one field holds given values, another field may hold only given
  values.

## Domains of the exploration methods

The field schema marks a field as mandatory for borehole and mine data, for probe sensing, or
for both. The domain of a child is read from its exploration method, as follows. The mapping
awaits confirmation by the data assessment team in
<https://github.com/ihfc-iugg/ghfdb/issues/36>.

{{ domains() }}

## The rules

{{ entries() }}

## Rules under discussion

These questions are open with the data assessment team. Until they are settled, the check does
not apply the rules they would add.

* <https://github.com/ihfc-iugg/ghfdb/issues/30>: temperature methods for an indirect
  exploration method.
* <https://github.com/ihfc-iugg/ghfdb/issues/31>: temperature methods for probe-sensing data.
* <https://github.com/ihfc-iugg/ghfdb/issues/32>: the in-situ flag and the pressure and
  temperature conditions.
* <https://github.com/ihfc-iugg/ghfdb/issues/33>: the pressure and temperature conditions and
  the pressure and temperature function.
* <https://github.com/ihfc-iugg/ghfdb/issues/34>: when the temperature correction methods
  apply.
* <https://github.com/ihfc-iugg/ghfdb/issues/35>: whether the conductivity method is mandatory
  for borehole data.
* <https://github.com/ihfc-iugg/ghfdb/issues/36>: the domain of each exploration method.
