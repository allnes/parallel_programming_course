"""User-facing strings for scoreboard pages."""

TEXT = {
    # Titles
    "title": "Parallel Programming Scoreboard",
    "threads_title": "Threads Track Scoreboard",
    "processes_title": "Processes Track Scoreboard",
    "variants_title": "Variant Calculator",
    # Common labels
    "generated_label": "Generated (MSK):",
    "back_to_index": "\u2190 Back to Index",
    # Page headings
    "pages_heading": "Pages",
    "groups_heading": "Groups",
    "threads_group_heading": "Threads",
    "processes_group_heading": "Processes",
    "no_group_pages": "No group pages",
    # Legends
    "legend_heading": "Legend",
    "legend_table": [
        "V — variant",
        "R — report",
        "S — solution",
        "P — performance points",
        "A — acceleration",
        "E — efficiency",
        "D — deadline delta",
        "C — copying penalty",
    ],
    "legend_pairs": [
        ("(V)ariant", "Task variant number assigned to the student."),
        ("(R)eport", "Task report in Markdown (.md), required."),
        ("(S)olution", "The correctness and completeness of the implemented solution."),
        ("(A)cceleration", "Speedup = T(seq) / T(parallel)."),
        ("(E)fficiency", "Efficiency = Speedup / NumProcs."),
        ("(P)erformance", "Points awarded based on efficiency thresholds (see docs)."),
        ("(D)eadline", "Timeliness vs deadline (due at 23:59 MSK on the shown date)."),
        ("(C)opying", "Penalty for detected copying cases."),
    ],
    # Calculator
    "variant_hint": "Threads have 1 variant; Processes have 3 variants (tasks 1/2/3).",
    "variant_calc_title": "Compute my variant",
    "fill_prompt": "Fill Last, First, Group",
    "threads_label": "Threads",
    "processes_label": "Processes",
    "threads_variant_label": "Threads",
    "processes_variant_label": "Processes",
    "variant_texts": {
        "fillPrompt": "Fill Last, First, Group",
        "threadsLabel": "Threads",
        "processesLabel": "Processes",
        "threadsVariantLabel": "Threads",
        "processesVariantLabel": "Processes",
    },
    "variant_legend_threads": "Threads — variant for threads tasks.",
    "variant_legend_processes": "Processes — variants for task-1/2/3.",
    "variant_form_last": "Last name",
    "variant_form_first": "First name",
    "variant_form_middle": "Middle name",
    "variant_form_group": "Group",
    "variant_form_button": "Compute",
}
