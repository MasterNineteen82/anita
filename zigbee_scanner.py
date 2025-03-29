import asyncio
import logging
import os
import json
import csv
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.tree import Tree
from rich.text import Text
from rich.logging import RichHandler
from rich.prompt import Confirm

# Configure logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("ZigbeeScanner")

# Import zigpy components
from zigpy.application import ControllerApplication
from zigpy.config import CONF_DEVICE, CONF_DEVICE_PATH
from zigpy.exceptions import NetworkNotFormed
from zigpy_znp.zigbee.application import ControllerApplication as ZNPControllerApplication
try:
    from zigpy_deconz.zigbee.application import ControllerApplication as DeconzControllerApplication
    DECONZ_AVAILABLE = True
except ImportError:
    DECONZ_AVAILABLE = False
try:
    from zigpy_xbee.zigbee.application import ControllerApplication as XBeeControllerApplication
    XBEE_AVAILABLE = True
except ImportError:
    XBEE_AVAILABLE = False
try:
    from zigpy_zigate.zigbee.application import ControllerApplication as ZiGateControllerApplication
    ZIGATE_AVAILABLE = True
except ImportError:
    ZIGATE_AVAILABLE = False

# Default port for Zigbee USB dongle
DEFAULT_PORT = 'COM3'  # Change this to match your system
DEFAULT_SCAN_DURATION = 60  # seconds

# Rich Console for styled output
console = Console()

# Known device types and their icons
DEVICE_ICONS = {
    "router": "🔄",
    "end": "🔹",
    "coordinator": "🌟",
    "unknown": "❓"
}

# Common Zigbee clusters and their descriptions
CLUSTERS = {
    0x0000: "Basic",
    0x0001: "Power Configuration",
    0x0003: "Identify",
    0x0006: "On/Off",
    0x0008: "Level Control",
    0x0009: "Alarms",
    0x000A: "Time",
    0x000F: "Binary Input Basic",
    0x0019: "OTA",
    0x0020: "Poll Control",
    0x0201: "Thermostat",
    0x0300: "Color Control",
    0x0400: "Illuminance Measurement",
    0x0402: "Temperature Measurement",
    0x0403: "Pressure Measurement",
    0x0405: "Humidity Measurement",
    0x0406: "Occupancy Sensing",
    0x0500: "IAS Zone",
    0x0702: "Metering",
    0x0B05: "Diagnostics",
}

class ZigbeeScanner:
    def __init__(self, port=None, adapter_type="znp", scan_duration=DEFAULT_SCAN_DURATION):
        self.port = port or DEFAULT_PORT
        self.adapter_type = adapter_type.lower()
        self.scan_duration = scan_duration
        self.app = None
        self.devices = {}
        
    async def connect(self):
        """Connect to the Zigbee dongle and initialize the network."""
        with console.status(f"[bold blue]Connecting to {self.adapter_type.upper()} Zigbee adapter on {self.port}...[/bold blue]"):
            logger.info(f"Connecting to {self.adapter_type.upper()} Zigbee adapter on {self.port}")
            
            config = {
                CONF_DEVICE: {
                    CONF_DEVICE_PATH: self.port,
                }
            }
            
            try:
                # Select the appropriate controller application based on adapter type
                if self.adapter_type == "znp":
                    self.app = await ZNPControllerApplication.new(config)
                elif self.adapter_type == "deconz" and DECONZ_AVAILABLE:
                    self.app = await DeconzControllerApplication.new(config)
                elif self.adapter_type == "xbee" and XBEE_AVAILABLE:
                    self.app = await XBeeControllerApplication.new(config)
                elif self.adapter_type == "zigate" and ZIGATE_AVAILABLE:
                    self.app = await ZiGateControllerApplication.new(config)
                else:
                    raise ValueError(f"Unsupported adapter type: {self.adapter_type}")
                
                # Start the network
                try:
                    await self.app.startup()
                except NetworkNotFormed:
                    console.print(Panel("[yellow]Network not formed, forming new network...[/yellow]", 
                                      title="Network Status", border_style="yellow"))
                    logger.info("Network not formed, forming network...")
                    await self.app.form_network()
                
                # Display network information
                self._display_network_info()
                return True
                
            except Exception as e:
                console.print(Panel(f"[bold red]Failed to connect: {str(e)}[/bold red]", 
                                  title="Error", border_style="red"))
                logger.error(f"Error connecting to Zigbee adapter: {e}")
                return False
    
    def _display_network_info(self):
        """Display formatted network information."""
        if not self.app:
            return
            
        network_info = Panel(
            f"[bold white]PAN ID:[/bold white] [cyan]0x{self.app.ieee:016x}[/cyan]\n"
            f"[bold white]Extended PAN ID:[/bold white] [cyan]0x{self.app.extended_pan_id:016x}[/cyan]\n"
            f"[bold white]Channel:[/bold white] [cyan]{self.app.channel}[/cyan]\n"
            f"[bold white]Network Key:[/bold white] [cyan]{':'.join(f'{b:02x}' for b in self.app.tc_link_key.key)}[/cyan]",
            title="[bold green]Zigbee Network Information[/bold green]",
            border_style="green"
        )
        console.print(network_info)
    
    async def scan_network(self):
        """Scan the Zigbee network for devices."""
        if not self.app:
            console.print("[bold red]Not connected to any Zigbee adapter![/bold red]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            TextColumn("[bold]{task.completed}/{task.total}[/bold]"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Start the permit joining process
            scan_task = progress.add_task(
                f"Scanning Zigbee network for {self.scan_duration} seconds...", 
                total=self.scan_duration
            )
            
            # Permit joining
            await self.app.permit_ncp(self.scan_duration)
            
            # Show progress while waiting
            for i in range(self.scan_duration):
                if progress.finished:
                    break
                progress.update(scan_task, completed=i + 1)
                await asyncio.sleep(1)
                
                # Refresh device list periodically during scan
                if i % 5 == 0 and self.app.devices:
                    self.devices = self.app.devices
                    progress.console.print(f"[green]Found {len(self.devices)} devices so far...[/green]")
        
        # Update final device list
        self.devices = self.app.devices
        return self.devices
    
    def display_devices(self, detailed=True):
        """Display discovered devices in a table and detailed view."""
        if not self.devices:
            console.print(Panel("[yellow]No devices found in the network[/yellow]", 
                              title="Scan Results", border_style="yellow"))
            return
            
        # Display devices in a table
        devices_table = Table(title=f"Discovered Zigbee Devices ({len(self.devices)})")
        devices_table.add_column("Icon", justify="center", no_wrap=True)
        devices_table.add_column("IEEE", style="magenta")
        devices_table.add_column("NWK", style="blue")
        devices_table.add_column("Type", style="cyan")
        devices_table.add_column("Manufacturer", style="green")
        devices_table.add_column("Model", style="yellow")
        devices_table.add_column("Name", style="red")
        devices_table.add_column("Endpoints", style="white")
        
        for ieee, dev in self.devices.items():
            # Determine device type and icon
            if dev.node_desc and dev.node_desc.logical_type is not None:
                device_type = dev.node_desc.logical_type.name
                icon = DEVICE_ICONS.get(device_type.lower(), DEVICE_ICONS["unknown"])
            else:
                device_type = "Unknown"
                icon = DEVICE_ICONS["unknown"]
                
            endpoints = list(dev.endpoints.keys())
            devices_table.add_row(
                icon,
                str(ieee),
                f"0x{dev.nwk:04x}",
                device_type,
                str(dev.manufacturer) if dev.manufacturer else "Unknown",
                str(dev.model) if dev.model else "Unknown",
                str(dev.name) if dev.name else "Unknown",
                str(endpoints)
            )
        
        console.print(devices_table)
        
        # Detailed device information if requested
        if detailed:
            console.print(Panel("[bold]Detailed Device Information[/bold]", 
                              border_style="blue"))
            
            for ieee, dev in self.devices.items():
                device_tree = Tree(f"[bold cyan]{ieee}[/bold cyan] - [yellow]0x{dev.nwk:04x}[/yellow]")
                
                device_tree.add(f"Manufacturer: [green]{dev.manufacturer or 'Unknown'}[/green]")
                device_tree.add(f"Model: [yellow]{dev.model or 'Unknown'}[/yellow]")
                device_tree.add(f"Name: [red]{dev.name or 'Unknown'}[/red]")
                
                # Add node descriptor info if available
                if dev.node_desc:
                    node_branch = device_tree.add(f"[bold]Node Descriptor[/bold]")
                    if dev.node_desc.logical_type is not None:
                        node_branch.add(f"Type: [cyan]{dev.node_desc.logical_type.name}[/cyan]")
                    if dev.node_desc.is_mains_powered is not None:
                        power_source = "Mains Powered" if dev.node_desc.is_mains_powered else "Battery Powered"
                        node_branch.add(f"Power Source: [cyan]{power_source}[/cyan]")
                
                # Add endpoints information
                endpoints_branch = device_tree.add(f"[bold]Endpoints: {list(dev.endpoints.keys())}[/bold]")
                
                for ep_id, endpoint in dev.endpoints.items():
                    if ep_id == 0:  # Skip ZDO endpoint
                        continue
                        
                    ep_branch = endpoints_branch.add(f"[bold]Endpoint {ep_id}[/bold]")
                    ep_branch.add(f"Profile: [blue]0x{endpoint.profile_id:04x}[/blue]")
                    ep_branch.add(f"Device Type: [blue]0x{endpoint.device_type:04x}[/blue]")
                    
                    # Input clusters
                    in_clusters_branch = ep_branch.add("[bold green]Input Clusters:[/bold green]")
                    for cluster_id in endpoint.in_clusters.keys():
                        cluster_name = CLUSTERS.get(cluster_id, "Unknown")
                        in_clusters_branch.add(f"0x{cluster_id:04x} - {cluster_name}")
                    
                    # Output clusters
                    out_clusters_branch = ep_branch.add("[bold yellow]Output Clusters:[/bold yellow]")
                    for cluster_id in endpoint.out_clusters.keys():
                        cluster_name = CLUSTERS.get(cluster_id, "Unknown")
                        out_clusters_branch.add(f"0x{cluster_id:04x} - {cluster_name}")
                
                console.print(device_tree)
                console.print("")
    
    async def generate_report(self, format_type="txt", filename=None):
        """Generate a report of discovered devices in the specified format."""
        if not self.devices:
            console.print("[yellow]No devices to report[/yellow]")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            filename = f"zigbee_devices_{timestamp}"
        
        # Ensure directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        if format_type == "txt":
            file_path = reports_dir / f"{filename}.txt"
            with open(file_path, "w") as report_file:
                report_file.write(f"Zigbee Network Scan Report - {datetime.now()}\n")
                report_file.write(f"PAN ID: 0x{self.app.ieee:016x}\n")
                report_file.write(f"Extended PAN ID: 0x{self.app.extended_pan_id:016x}\n")
                report_file.write(f"Channel: {self.app.channel}\n\n")
                report_file.write(f"Found {len(self.devices)} devices:\n")
                
                for ieee, dev in self.devices.items():
                    report_file.write(f"Device: {ieee}\n")
                    report_file.write(f"  NWK: 0x{dev.nwk:04x}\n")
                    report_file.write(f"  Manufacturer: {dev.manufacturer or 'Unknown'}\n")
                    report_file.write(f"  Model: {dev.model or 'Unknown'}\n")
                    report_file.write(f"  Name: {dev.name or 'Unknown'}\n")
                    
                    if dev.node_desc and dev.node_desc.logical_type is not None:
                        report_file.write(f"  Type: {dev.node_desc.logical_type.name}\n")
                    
                    report_file.write(f"  Endpoints: {list(dev.endpoints.keys())}\n\n")
                    
                    # Add endpoint details
                    for ep_id, endpoint in dev.endpoints.items():
                        if ep_id == 0:  # Skip ZDO endpoint
                            continue
                        report_file.write(f"    Endpoint {ep_id}:\n")
                        report_file.write(f"      Profile: 0x{endpoint.profile_id:04x}\n")
                        report_file.write(f"      Device Type: 0x{endpoint.device_type:04x}\n")
                        report_file.write(f"      Input clusters: {list(endpoint.in_clusters.keys())}\n")
                        report_file.write(f"      Output clusters: {list(endpoint.out_clusters.keys())}\n\n")
        
        elif format_type == "json":
            file_path = reports_dir / f"{filename}.json"
            network_data = {
                "timestamp": str(datetime.now()),
                "network": {
                    "pan_id": f"0x{self.app.ieee:016x}",
                    "extended_pan_id": f"0x{self.app.extended_pan_id:016x}",
                    "channel": self.app.channel
                },
                "devices": {}
            }
            
            for ieee, dev in self.devices.items():
                device_data = {
                    "ieee": str(ieee),
                    "nwk": f"0x{dev.nwk:04x}",
                    "manufacturer": str(dev.manufacturer) if dev.manufacturer else "Unknown",
                    "model": str(dev.model) if dev.model else "Unknown",
                    "name": str(dev.name) if dev.name else "Unknown",
                    "type": str(dev.node_desc.logical_type.name) if dev.node_desc and dev.node_desc.logical_type is not None else "Unknown",
                    "endpoints": {}
                }
                
                for ep_id, endpoint in dev.endpoints.items():
                    if ep_id == 0:  # Skip ZDO endpoint
                        continue
                    device_data["endpoints"][str(ep_id)] = {
                        "profile": f"0x{endpoint.profile_id:04x}",
                        "device_type": f"0x{endpoint.device_type:04x}",
                        "in_clusters": [f"0x{c:04x}" for c in endpoint.in_clusters.keys()],
                        "out_clusters": [f"0x{c:04x}" for c in endpoint.out_clusters.keys()]
                    }
                
                network_data["devices"][str(ieee)] = device_data
            
            with open(file_path, "w") as json_file:
                json.dump(network_data, json_file, indent=2)
        
        elif format_type == "csv":
            file_path = reports_dir / f"{filename}.csv"
            with open(file_path, "w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["IEEE", "NWK", "Type", "Manufacturer", "Model", "Name", "Endpoints"])
                
                for ieee, dev in self.devices.items():
                    device_type = str(dev.node_desc.logical_type.name) if dev.node_desc and dev.node_desc.logical_type is not None else "Unknown"
                    writer.writerow([
                        str(ieee),
                        f"0x{dev.nwk:04x}",
                        device_type,
                        str(dev.manufacturer) if dev.manufacturer else "Unknown",
                        str(dev.model) if dev.model else "Unknown",
                        str(dev.name) if dev.name else "Unknown",
                        str(list(dev.endpoints.keys()))
                    ])
        
        else:
            console.print(f"[bold red]Unsupported report format: {format_type}[/bold red]")
            return None
        
        console.print(Panel(f"[bold green]Report saved to {file_path}[/bold green]", 
                          title="Report Generated", border_style="green"))
        logger.info(f"Report saved to {file_path}")
        return file_path
    
    async def shutdown(self):
        """Shutdown the Zigbee controller."""
        if self.app:
            console.print("[bold blue]Shutting down Zigbee controller...[/bold blue]")
            await self.app.shutdown()
            console.print("[bold green]Zigbee controller shut down successfully[/bold green]")

async def interactive_scan(args):
    """Run an interactive Zigbee network scan."""
    scanner = ZigbeeScanner(
        port=args.port, 
        adapter_type=args.adapter, 
        scan_duration=args.duration
    )
    
    try:
        # Connect to the adapter
        if not await scanner.connect():
            return
        
        # Scan the network
        console.print(Panel(
            f"[bold]Starting Zigbee network scan for {args.duration} seconds...[/bold]\n"
            "[italic]Devices will be displayed as they are discovered[/italic]",
            title="Scan Started",
            border_style="blue"
        ))
        
        await scanner.scan_network()
        
        # Display the results
        console.print(Panel(
            f"[bold green]Scan complete! Found {len(scanner.devices)} devices.[/bold green]",
            border_style="green"
        ))
        
        scanner.display_devices(detailed=args.verbose)
        
        # Generate reports
        if args.format:
            formats = args.format.split(',')
            for fmt in formats:
                await scanner.generate_report(format_type=fmt.strip(), filename=args.output)
        
        # Monitor mode if enabled
        if args.monitor and scanner.devices:
            console.print(Panel(
                "[bold yellow]Entering monitor mode. Press Ctrl+C to exit.[/bold yellow]",
                border_style="yellow"
            ))
            
            try:
                while True:
                    console.print("[blue]Monitoring network...[/blue]")
                    await asyncio.sleep(10)
                    # Here you could add code to check device status, etc.
            except asyncio.CancelledError:
                console.print("[yellow]Monitor mode cancelled[/yellow]")
            
    except KeyboardInterrupt:
        console.print("[yellow]Scan interrupted by user[/yellow]")
    except Exception as e:
        console.print_exception(show_locals=args.debug)
        logger.error(f"Error during scan: {e}")
    finally:
        # Shutdown the controller
        await scanner.shutdown()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Enhanced Zigbee Network Scanner')
    
    # Required arguments
    parser.add_argument('--port', '-p', help=f'Serial port for the Zigbee adapter (default: {DEFAULT_PORT})')
    
    # Optional arguments
    parser.add_argument('--adapter', '-a', choices=['znp', 'deconz', 'xbee', 'zigate'], default='znp',
                      help='Type of Zigbee adapter (default: znp)')
    parser.add_argument('--duration', '-d', type=int, default=DEFAULT_SCAN_DURATION,
                      help=f'Duration in seconds to scan for devices (default: {DEFAULT_SCAN_DURATION})')
    parser.add_argument('--format', '-f', 
                      help='Output format(s) for the report (txt,json,csv - comma separated)')
    parser.add_argument('--output', '-o', 
                      help='Base filename for reports (without extension)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Display detailed device information')
    parser.add_argument('--monitor', '-m', action='store_true',
                      help='Enter monitor mode after scanning')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode with detailed error information')
    
    args = parser.parse_args()
    
    # Print banner
    console.print(Panel.fit(
        "[bold blue]Zigbee Network Scanner[/bold blue]\n"
        "[italic]Discover and analyze Zigbee devices on your network[/italic]",
        border_style="cyan"
    ))
    
    try:
        asyncio.run(interactive_scan(args))
    except KeyboardInterrupt:
        console.print("[bold yellow]Program interrupted by user[/bold yellow]")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            console.print_exception()
        else:
            console.print(f"[bold red]Error: {e}[/bold red]")

if __name__ == "__main__":
    main()