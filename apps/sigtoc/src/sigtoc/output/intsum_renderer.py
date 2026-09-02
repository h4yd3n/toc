from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

class INTSUMRenderer:
    @staticmethod
    def render_markdown(
        date_str: str, 
        bluf: str, 
        pir_statuses: List[dict], 
        significant_signals: List[dict], 
        score_changes: List[dict], 
        active_travel: List[dict], 
        collection_gaps: List[dict]
    ) -> str:
        """
        Formats INTSUM matching PRD §4.1.7 template.
        """
        lines = []
        lines.append(f"# INTELLIGENCE SUMMARY (INTSUM) - {date_str}")
        lines.append("")
        
        lines.append("## BOTTOM LINE UP FRONT (BLUF)")
        lines.append(bluf)
        lines.append("")
        
        lines.append("## PRIORITY INTELLIGENCE REQUIREMENTS (PIR) STATUS")
        for pir in pir_statuses:
            lines.append(f"- **{pir['id']}**: {pir['status']}")
        lines.append("")
        
        lines.append("## SIGNIFICANT SIGNALS")
        for sig in significant_signals:
            lines.append(f"- **{sig['source']}**: {sig['summary']} (Credibility: {sig['credibility']})")
        lines.append("")
        
        lines.append("## SCORE CHANGES")
        for sc in score_changes:
            lines.append(f"- {sc['entity']}: {sc['old']} -> {sc['new']} ({sc['reason']})")
        lines.append("")
        
        lines.append("## ACTIVE TRAVEL")
        for at in active_travel:
            lines.append(f"- **{at['person']}**: {at['location']} (Risk: {at['risk']})")
        lines.append("")
        
        lines.append("## COLLECTION GAPS")
        for gap in collection_gaps:
            lines.append(f"- {gap['description']}")
        lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def render_terminal(
        date_str: str, 
        bluf: str, 
        pir_statuses: List[dict], 
        significant_signals: List[dict], 
        score_changes: List[dict], 
        active_travel: List[dict], 
        collection_gaps: List[dict]
    ) -> None:
        console = Console()
        
        console.print(f"[bold green]INTELLIGENCE SUMMARY (INTSUM) - {date_str}[/bold green]")
        console.print()
        
        bluf_panel = Panel(
            bluf,
            title="BOTTOM LINE UP FRONT (BLUF)",
            border_style="yellow"
        )
        console.print(bluf_panel)
        console.print()
        
        # PIR Table
        if pir_statuses:
            pir_table = Table(title="PIR Status", box=box.SIMPLE)
            pir_table.add_column("PIR ID", style="cyan")
            pir_table.add_column("Status")
            for pir in pir_statuses:
                pir_table.add_row(pir['id'], pir['status'])
            console.print(pir_table)
            console.print()
            
        # Significant Signals Table
        if significant_signals:
            sig_table = Table(title="Significant Signals", box=box.SIMPLE)
            sig_table.add_column("Source", style="magenta")
            sig_table.add_column("Summary")
            sig_table.add_column("Credibility")
            for sig in significant_signals:
                sig_table.add_row(sig['source'], sig['summary'], str(sig['credibility']))
            console.print(sig_table)
            console.print()
            
        # Active Travel
        if active_travel:
            travel_table = Table(title="Active Travel", box=box.SIMPLE)
            travel_table.add_column("Person", style="blue")
            travel_table.add_column("Location")
            travel_table.add_column("Risk")
            for at in active_travel:
                travel_table.add_row(at['person'], at['location'], at['risk'])
            console.print(travel_table)
            console.print()
            
        if collection_gaps:
            console.print("[bold yellow]Collection Gaps:[/bold yellow]")
            for gap in collection_gaps:
                console.print(f"- {gap['description']}")
