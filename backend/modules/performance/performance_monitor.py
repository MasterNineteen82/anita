import time
import threading
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PerformanceMonitor:
    """
    A class to monitor system performance metrics like CPU usage, memory usage,
    disk I/O, and network I/O. It logs these metrics periodically.
    """

    def __init__(self, interval=5, log_level=logging.INFO):
        """
        Initializes the PerformanceMonitor.

        Args:
            interval (int): Time interval (in seconds) between each monitoring cycle.
            log_level (int):  Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        self.interval = interval
        self.log_level = log_level
        self._stop_event = threading.Event()  # Used to signal the monitoring thread to stop
        self._thread = None  # Will hold the monitoring thread

    def _get_cpu_usage(self):
        """Returns the current CPU utilization percentage."""
        return psutil.cpu_percent(interval=0.1)  # Short interval for more responsive reading

    def _get_memory_usage(self):
        """Returns the current memory usage statistics."""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent
        }

    def _get_disk_io_counters(self):
        """Returns disk I/O statistics."""
        disk_io = psutil.disk_io_counters()
        return {
            'read_count': disk_io.read_count,
            'write_count': disk_io.write_count,
            'read_bytes': disk_io.read_bytes,
            'write_bytes': disk_io.write_bytes
        }

    def _get_network_io_counters(self):
        """Returns network I/O statistics."""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }

    def _log_performance_metrics(self):
        """Collects and logs performance metrics."""
        cpu_usage = self._get_cpu_usage()
        memory_usage = self._get_memory_usage()
        disk_io = self._get_disk_io_counters()
        network_io = self._get_network_io_counters()

        logging.log(self.log_level, f"CPU Usage: {cpu_usage}%")
        logging.log(self.log_level, f"Memory Usage: {memory_usage['percent']}% "
                      f"(Used: {memory_usage['used']/ (1024 * 1024):.2f} MB, "
                      f"Available: {memory_usage['available']/ (1024 * 1024):.2f} MB)")
        logging.log(self.log_level, f"Disk I/O: Read {disk_io['read_bytes']/ (1024):.2f} KB, "
                      f"Write {disk_io['write_bytes']/ (1024):.2f} KB")
        logging.log(self.log_level, f"Network I/O: Sent {network_io['bytes_sent']/ (1024):.2f} KB, "
                      f"Received {network_io['bytes_recv']/ (1024):.2f} KB")

    def start_monitoring(self):
        """Starts the performance monitoring in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("Performance monitor is already running.")
            return

        self._stop_event.clear()  # Ensure the stop event is cleared before starting
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logging.info("Performance monitor started.")

    def stop_monitoring(self):
        """Stops the performance monitoring thread."""
        if self._thread is None or not self._thread.is_alive():
            logging.warning("Performance monitor is not running.")
            return

        self._stop_event.set()  # Signal the thread to stop
        self._thread.join()  # Wait for the thread to finish
        self._thread = None
        logging.info("Performance monitor stopped.")

    def _monitoring_loop(self):
        """The main loop that runs in the monitoring thread."""
        while not self._stop_event.is_set():
            self._log_performance_metrics()
            time.sleep(self.interval)

    def __enter__(self):
         """Allows the PerformanceMonitor to be used as a context manager."""
         self.start_monitoring()
         return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stops the monitor when exiting the context."""
        self.stop_monitoring()

if __name__ == '__main__':
    # Example Usage:
    try:
        with PerformanceMonitor(interval=2, log_level=logging.DEBUG) as monitor:
            time.sleep(10)  # Monitor performance for 10 seconds
        print("Monitoring finished.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")