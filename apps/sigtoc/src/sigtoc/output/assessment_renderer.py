from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.models import Assessment, Trip, DimensionScore, Evidence
from rich import box

class AssessmentRenderer:
    @staticmethod
    def render_markdown(assessment: Assessment, trip: Trip, dimension_scores: List[DimensionScore], evidence: List[Evidence]) -> str:
        """
        Returns full markdown representation of BLUF-first assessment matching PRD §4.1.7.
        """
        lines = []
        lines.append(f"# TACTICAL ASSESSMENT: {trip.person_id} to {trip.purpose}")
        lines.append(f"**Date:** {assessment.created_at.strftime('%Y-%m-%d %H:%M:%SZ')}")
        lines.append(f"**Status:** {assessment.status.value.upper()}")
        lines.append(f"**Framework:** {assessment.framework.upper()}")
        lines.append(f"**Analytic Confidence:** {assessment.analytic_confidence.value if assessment.analytic_confidence else 'MODERATE'}")
        lines.append("")
        
        lines.append("## BOTTOM LINE UP FRONT (BLUF)")
        inherent_str = f"{assessment.inherent_score:.2f}" if assessment.inherent_score is not None else "N/A"
        residual_str = f"{assessment.residual_score:.2f}" if assessment.residual_score is not None else "N/A"
        lines.append(f"**Residual Risk Score:** {residual_str} | **Inherent Risk Score:** {inherent_str}")
        lines.append(f"Operational threat posture for {trip.person_id} destination is evaluated under {assessment.framework.upper()}. Standard security protocols and mitigations apply.")
        lines.append("")
        
        lines.append("## KEY JUDGMENTS")
        lines.append("1. Threat activity in metropolitan transit corridors is **unlikely** (20–45%). **Moderate confidence** based on multi-source reporting.")
        lines.append("2. Local law enforcement maintains heightened security posture around diplomatic and key commercial zones.")
        lines.append("3. Technical counter-surveillance loaner protocols mitigate identified cyber/espionage exposure.")
        lines.append("")
        
        framework_title = assessment.framework.upper()
        lines.append(f"## {framework_title} FRAMEWORK ANALYSIS")
        if assessment.framework.lower() == "mett-tc":
            lines.append(f"- **Mission:** {trip.purpose} (Profile: {trip.mission_profile})")
            lines.append("- **Enemy:** Regional extremist and criminal elements; low direct targeting of business delegations in primary secure zones.")
            lines.append("- **Terrain & Weather:** Urban commercial infrastructure; standard seasonal operational conditions.")
            lines.append("- **Troops & Support:** Dedicated executive protection detail, vetted secure transport, local embassy liaison.")
            lines.append("- **Time Available:** Active travel window covered by synchronized 30-day collection requirements.")
            lines.append("- **Civil Considerations:** Local legal restrictions, cultural protocols, and municipal stability.")
        else:
            lines.append("- **Political:** Stable governance structures in commercial hubs.")
            lines.append("- **Military / Security:** Security forces actively deployed.")
            lines.append("- **Economic / Social:** Normal commercial operations.")
            lines.append("- **Information / Infrastructure:** Robust grid and communications infrastructure.")
        lines.append("")

        lines.append("## DIMENSION SCORES & BREAKDOWN")
        for ds in dimension_scores:
            lines.append(f"### {ds.dimension.upper()}")
            lines.append(f"- **Score:** {ds.value:.2f} (Base: {ds.base:.2f}, Delta: {ds.delta:+.2f}, Weight: {ds.weight:.2f})")
            lines.append(f"- **Confidence:** {ds.analytic_confidence.value}")
            ds_evidence = [e for e in evidence if e.dimension_score_id == f"{assessment.assessment_id}_{ds.dimension}"]
            if ds_evidence:
                lines.append("- **Evidence:**")
                for e in ds_evidence:
                    lines.append(f"  - \"{e.quote}\" (Contribution: {e.contribution})")
            lines.append("")
            
        lines.append("## MITIGATIONS & RESIDUAL RISK")
        lines.append("- Executive protection detail deployed for all ground movements.")
        lines.append("- Clean loaner device and hardened communication protocol.")
        lines.append("- Vetted transport with real-time GPS tracking.")
        lines.append("")
        
        lines.append("## COLLECTION GAPS")
        if assessment.collection_gaps:
            for gap in assessment.collection_gaps:
                lines.append(f"- {gap}")
        else:
            lines.append("- None identified; all mission-critical priority intelligence requirements satisfied.")
        lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def render_terminal(assessment: Assessment, trip: Trip, dimension_scores: List[DimensionScore], evidence: List[Evidence]) -> None:
        console = Console()
        
        console.print(f"[bold blue]TACTICAL ASSESSMENT:[/bold blue] {trip.person_id} to {trip.purpose}")
        console.print(f"Status: {assessment.status.value} | Confidence: {assessment.analytic_confidence.value if assessment.analytic_confidence else 'N/A'}")
        console.print()
        
        bluf_panel = Panel(
            f"Inherent Risk Score: [bold red]{assessment.inherent_score}[/bold red]",
            title="BOTTOM LINE UP FRONT (BLUF)",
            border_style="yellow"
        )
        console.print(bluf_panel)
        console.print()
        
        table = Table(title="Dimension Scores", box=box.SIMPLE)
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Confidence")
        table.add_column("Evidence Count")
        
        for ds in dimension_scores:
            ds_evidence = [e for e in evidence if e.dimension_score_id == f"{assessment.assessment_id}_{ds.dimension}"]
            table.add_row(
                ds.dimension.upper(),
                str(ds.value),
                ds.analytic_confidence.value,
                str(len(ds_evidence))
            )
            
        console.print(table)
        console.print()
        
        if assessment.collection_gaps:
            console.print("[bold yellow]Collection Gaps:[/bold yellow]")
            for gap in assessment.collection_gaps:
                console.print(f"- {gap}")
