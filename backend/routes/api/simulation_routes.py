from flask import Blueprint

simulation_bp = Blueprint('simulation', __name__, url_prefix='/api/simulation')

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    return "Simulation started"

@simulation_bp.route('/status', methods=['GET'])
def get_simulation_status():
    return "Simulation status"

@simulation_bp.route('/stop', methods=['POST'])
def stop_simulation():
    return "Simulation stopped"