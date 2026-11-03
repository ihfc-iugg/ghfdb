# Triage Labels

Automated workflows and written processes refer to issues by a canonical role. This file maps each
role to the label string this repository's tracker uses.

| Role              | Label in this tracker | Meaning                                              |
| ----------------- | --------------------- | ---------------------------------------------------- |
| `needs-triage`    | `needs-triage`        | Maintainer needs to evaluate this issue              |
| `needs-info`      | `needs-info`          | Waiting on the reporter for more information         |
| `ready-for-agent` | `ready-for-agent`     | Fully specified, ready for an unattended agent       |
| `ready-for-human` | `ready-for-human`     | Cannot be automated, needs a person to carry it out  |
| `wontfix`         | `wontfix`             | Will not be actioned                                 |

A request that needs scientific judgement, such as a new quality rule, a change to a penalty or a ruling where Fuchs et al. (2023) is ambiguous, is `ready-for-human` until it has been agreed in the issue.
