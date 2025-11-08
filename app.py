# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import math, threading, time

# ------------------------------
# APP SETUP
# ------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ------------------------------
# BUS DATA (SEATS + STATIC INFO)
# ------------------------------
# Note: 'buses' contains seat info and stop names for quick UI display.
# 'routes' below contains the coordinates for each stop used for simulation.
buses = {
    "BusA": {
        "name": "Bus A",
        "route": "Katpadi - Bagayam (Route 1)",
        "total_seats": 42,
        "available_seats": 32,
        "stops": [
            "Vallimalai Koot Road",
            "Uzhavar Sandhai (Farmer’s Market), Katpadi Govt. HSS",
            "Katpadi Junction Railway Station",
            "Chittoor Bus Stand",
            "Odai Pillaiyar Koil",
            "Silk Mill",
            "Kangeyanallur Road",
            "Viruthampet",
            "Vellore New Bus Stand",
            "Green Circle Signal",
            "National Pachaiyappas",
            "CMC (Christian Medical College)",
            "Vellore Old Bus Stand",
            "Raja Theatre",
            "Voorhees College",
            "Kaspa Roundtana",
            "Lakshmi Theatre",
            "Toll Gate",
            "Circuit House",
            "Allapuram",
            "Thorapadi",
            "Mgr selai",
            "Vellore central Jail",
            "Vellore female jail",
            "Thandhai Periyar Polytechnic college",
            "CMC bagayam Campus",
            "Bagayam"
        ]
    },
    "BusB": {
        "name": "Bus B",
        "route": "Bagayam - Katpadi (Route 2)",
        "total_seats": 42,
        "available_seats": 35,
        "stops": [
            "Bagayam",
            "Ooteri",
            "Virupatchipuram",
            "Kuppam",
            "Sainathapuram",
            "DKM College for Women",
            "Sankaranpalayam",
            "Velapadi",
            "Dhinakaran",
            "Eye Hospital (CMC Eye Hospital)",
            "Raja Theatre",
            "Vellore Old Bus Stand",
            "CMC (Christian Medical College)",
            "National Pachaiyappas",
            "Green Circle Signal",
            "Vellore New Bus Stand",
            "Viruthampet",
            "Kangeyanallur Road",
            "Silk Mill",
            "Odai Pillaiyar Koil",
            "Chittoor Bus Stand",
            "Katpadi Junction Railway Station",
            "Uzhavar Sandhai (Farmer’s Market)",
            "Vallimalai Koot Road"
        ]
    }
}

# ------------------------------
# ROUTES (stop coordinates) — used for simulation & map display
# ------------------------------
routes = {
    "BusA": [
        {"name": "Vallimalai Koot Road", "lat": 12.980006851024251, "lon": 79.1367005969659},
        {"name": "Uzhavar Sandhai / Katpadi Govt School", "lat": 12.973337311617323, "lon": 79.13698498304608},
        {"name": "Katpadi Junction", "lat": 12.97087989374402, "lon": 79.13712402936956},
        {"name": "Chittoor Bus Stand", "lat": 12.96585650547078, "lon": 79.1372504488863},
        {"name": "Odai Pillaiyar Koil", "lat": 12.959242073164399, "lon": 79.13718787209929},
        {"name": "Silk Mill", "lat": 12.949788381583813, "lon": 79.13702408807158},
        {"name": "Kangeyanallur Road", "lat": 12.947115101258914, "lon": 79.13697600158129},
        {"name": "Viruthampet", "lat": 12.945936441884724, "lon": 79.13699589127368},
        {"name": "Vellore New Bus Stand", "lat": 12.9347076095303, "lon": 79.13560293393449},
        {"name": "Green Circle Signal", "lat": 12.932601035454612, "lon": 79.13782856201581},
        {"name": "National Pachaiyappas", "lat": 12.928862771931959, "lon": 79.13385072773515},
        {"name": "CMC", "lat": 12.924461469097304, "lon": 79.13337902441793},
        {"name": "Vellore Old Bus Stand", "lat": 12.919946127300875, "lon": 79.13203926240793},
        {"name": "Raja Theatre", "lat": 12.914935719015206, "lon": 79.13245484200017},
        {"name": "Voorhees College", "lat": 12.910807899347695, "lon": 79.13195559465684},
        {"name": "Kaspa Roundtana", "lat": 12.907022494810079, "lon": 79.13192281805382},
        {"name": "Lakshmi Theatre", "lat": 12.90276691107113, "lon": 79.1317315565256},
        {"name": "Toll Gate", "lat": 12.899722602109236, "lon": 79.13103503197901},
        {"name": "Circuit House", "lat": 12.897348413561327, "lon": 79.13021152182107},
        {"name": "Allapuram", "lat": 12.895012327594811, "lon": 79.12781712618349},
        {"name": "Thorapadi", "lat": 12.892559716597916, "lon": 79.12489459198655},
        {"name": "Mgr selai", "lat": 12.890628014762674, "lon": 79.12301258625696},
        {"name": "Vellore central Jail", "lat": 12.887640301605582, "lon": 79.12236251575973},
        {"name": "Vellore female jail", "lat": 12.88381379778708, "lon": 79.12315687604197},
        {"name": "Thandhai Periyar Polytechnic college", "lat": 12.879476381377389, "lon": 79.1231717113319},
        {"name": "CMC bagayam Campus", "lat": 12.879381141746656, "lon": 79.13385200987729},
        {"name": "Bagayam", "lat": 12.880244806991884, "lon": 79.13461683692577}
    ],
    "BusB": [
        {"name": "Bagayam", "lat": 12.880244806991884, "lon": 79.13461683692577},
        {"name": "Ooteri", "lat": 12.884368, "lon": 79.135644},
        {"name": "Virupatchipuram", "lat": 12.889837, "lon": 79.135796},
        {"name": "Kuppam", "lat": 12.892572464414675, "lon": 79.13564249023099},
        {"name": "Sainathapuram", "lat": 12.896897058510103, "lon": 79.13516736093563},
        {"name": "DKM College", "lat": 12.89958563227319, "lon": 79.1351116796563},
        {"name": "Sankaranpalayam", "lat": 12.901801595765367, "lon": 79.13532898645113},
        {"name": "Velapadi", "lat": 12.904786550010515, "lon": 79.13578070557476},
        {"name": "Dhinakaran", "lat": 12.908855632294944, "lon": 79.13329321092732},
        {"name": "Eye Hospital", "lat": 12.912449426550614, "lon": 79.13307350392738},
        {"name": "Raja Theatre", "lat": 12.914935719015206, "lon": 79.13245484200017},
        {"name": "Vellore Old Bus Stand", "lat": 12.919946127300875, "lon": 79.13203926240793},
        {"name": "CMC", "lat": 12.924461469097304, "lon": 79.13337902441793},
        {"name": "National Pachaiyappas", "lat": 12.928862771931959, "lon": 79.13385072773515},
        {"name": "Green Circle Signal", "lat": 12.932601035454612, "lon": 79.13782856201581},
        {"name": "Vellore New Bus Stand", "lat": 12.9347076095303, "lon": 79.13560293393449},
        {"name": "Viruthampet", "lat": 12.945936441884724, "lon": 79.13699589127368},
        {"name": "Kangeyanallur Road", "lat": 12.947115101258914, "lon": 79.13697600158129},
        {"name": "Silk Mill", "lat": 12.949788381583813, "lon": 79.13702408807158},
        {"name": "Odai Pillaiyar Koil", "lat": 12.959242073164399, "lon": 79.13718787209929},
        {"name": "Chittoor Bus Stand", "lat": 12.96585650547078, "lon": 79.1372504488863},
        {"name": "Katpadi Junction", "lat": 12.97087989374402, "lon": 79.13712402936956},
        {"name": "Uzhavar Sandhai", "lat": 12.973337311617323, "lon": 79.13698498304608},
        {"name": "Vallimalai Koot Road", "lat": 12.980006851024251, "lon": 79.1367005969659}
    ]
}

# ------------------------------
# ROUTES (for seats info)
# ------------------------------
@app.route('/')
def home():
    return "✅ Smart Bus Tracker Backend is running!"

@app.route('/buses')
def get_all_buses():
    # Return seat info + stop names (no coords here)
    return jsonify(buses)

@app.route('/bus/<bus_id>')
def get_bus(bus_id):
    bus = buses.get(bus_id)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404
    return jsonify(bus)

@app.route('/update_seats', methods=['POST'])
def update_seats():
    data = request.get_json()
    bus_id = data.get("bus_id")
    boarded = data.get("boarded", 0)
    alighted = data.get("alighted", 0)

    if bus_id not in buses:
        return jsonify({"error": "Bus not found"}), 404

    bus = buses[bus_id]
    total = bus["total_seats"]
    new_available = max(0, min(bus["available_seats"] - boarded + alighted, total))
    bus["available_seats"] = new_available

    return jsonify({
        "message": f"Seat count updated for {bus_id}",
        "available_seats": new_available,
        "total_seats": total
    }), 200

# ======================================================
#  🚍  REAL-TIME BUS MOVEMENT + LIVE ETA SIMULATION (IMPROVED)
# ======================================================

# Helper: haversine distance (meters)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000.0  # meters

# Simulation params
SPEED_KMH = 30.0
SPEED_MS = SPEED_KMH * 1000.0 / 3600.0  # ~8.333... m/s
REACHED_THRESHOLD_M = 150.0  # when bus is within this to a stop, mark reached

# Simulation state: store last passed stop index and current lat/lon
bus_state = {}
for bid, r in routes.items():
    bus_state[bid] = {
        "last_idx": 0,       # index of last stop passed (bus starts at stop 0)
        "lat": r[0]["lat"],
        "lon": r[0]["lon"]
    }

def advance_bus_one_tick(bid, dt=1.0):
    """
    Move bus 'bid' forward by dt seconds, at SPEED_MS, along the route defined in routes[bid].
    When close enough to the next stop, snap and mark it as passed.
    """
    route = routes[bid]
    state = bus_state[bid]
    n = len(route)
    last_idx = state["last_idx"]
    next_idx = (last_idx + 1) % n

    lat_cur, lon_cur = state["lat"], state["lon"]
    lat_next, lon_next = route[next_idx]["lat"], route[next_idx]["lon"]

    dist_to_next = haversine(lat_cur, lon_cur, lat_next, lon_next)
    if dist_to_next < 0.5:
        # Snap to next and advance index
        state["lat"], state["lon"] = lat_next, lon_next
        state["last_idx"] = next_idx
        return

    # Move along segment proportionally
    move_m = SPEED_MS * dt
    frac = min(1.0, move_m / dist_to_next)
    new_lat = lat_cur + (lat_next - lat_cur) * frac
    new_lon = lon_cur + (lon_next - lon_cur) * frac
    state["lat"], state["lon"] = new_lat, new_lon

    # If now within threshold of the next stop, snap and mark passed
    if haversine(new_lat, new_lon, lat_next, lon_next) <= REACHED_THRESHOLD_M:
        state["lat"], state["lon"] = lat_next, lon_next
        state["last_idx"] = next_idx

def simulate_loop(dt=1.0):
    """Background loop moving all buses every dt seconds."""
    while True:
        for bid in routes.keys():
            advance_bus_one_tick(bid, dt)
        time.sleep(dt)

# Start simulation thread
threading.Thread(target=simulate_loop, args=(1.0,), daemon=True).start()

def remaining_distance_along_route(bid, target_idx):
    """
    Compute remaining distance in meters along the route from the bus's current position to the target stop index.
    Accumulates segment distances forward along route order.
    """
    route = routes[bid]
    state = bus_state[bid]
    n = len(route)
    cur_lat, cur_lon = state["lat"], state["lon"]
    last_idx = state["last_idx"]

    # If target is the same as last_idx and the bus is exactly at that stop, distance = 0
    # We'll start by computing distance from current position to the next stop after last_idx (segment start)
    # Then walk segments until reaching target_idx.
    # Step 1: distance from current pos to next stop index after last_idx
    next_idx = (last_idx + 1) % n
    dist = 0.0

    # If the route only has 1 stop (unlikely), just compute direct dist
    if n == 1:
        return haversine(cur_lat, cur_lon, route[0]["lat"], route[0]["lon"])

    # distance from current position to next_idx stop
    dist += haversine(cur_lat, cur_lon, route[next_idx]["lat"], route[next_idx]["lon"])
    if next_idx == target_idx:
        return dist

    # accumulate full segments from next_idx -> ... -> target_idx
    i = next_idx
    while True:
        j = (i + 1) % n
        dist += haversine(route[i]["lat"], route[i]["lon"], route[j]["lat"], route[j]["lon"])
        if j == target_idx:
            break
        i = j

    return dist

@app.route("/live_status/<bus_id>", methods=["GET"])
def live_status(bus_id):
    """
    Returns current bus lat/lon plus ETA/distance/reached info for every stop (with stop coords).
    Response shape:
    {
      "bus_id": "BusA",
      "lat": ...,
      "lon": ...,
      "last_idx": 3,
      "etas": [
        {"index":0,"stop":"Vallimalai ...","lat":..,"lon":..,"distance_m":0,"eta_sec":0,"reached":true},
        {"index":1,"stop":"Uzhavar ...","lat":..,"lon":..,"distance_m":1200,"eta_sec":144,"reached":false},
        ...
      ]
    }
    """
    if bus_id not in routes:
        return jsonify({"error": "Bus not found"}), 404

    route = routes[bus_id]
    state = bus_state[bus_id]
    cur_lat = state["lat"]
    cur_lon = state["lon"]
    last_idx = state["last_idx"]
    n = len(route)

    # Build set of indices already passed in route order 0..last_idx (inclusive)
    passed_set = set()
    i = 0
    while True:
        passed_set.add(i)
        if i == last_idx:
            break
        i = (i + 1) % n

    etas = []
    for idx, stop in enumerate(route):
        # remaining distance along the route from current pos to this stop:
        rem_d = remaining_distance_along_route(bus_id, idx)
        # ETA seconds
        eta_sec = int(rem_d / SPEED_MS) if SPEED_MS > 0 else None

        # direct distance to stop (for rough proximity)
        direct_d = haversine(cur_lat, cur_lon, stop["lat"], stop["lon"])

        # Determine reached: either within threshold (direct proximity) OR the stop index is in passed_set
        reached = (direct_d <= REACHED_THRESHOLD_M) or (idx in passed_set)

        if reached:
            rem_d = 0
            eta_sec = 0

        etas.append({
            "index": idx,
            "stop": stop["name"],
            "lat": stop["lat"],
            "lon": stop["lon"],
            "distance_m": int(rem_d),
            "eta_sec": int(eta_sec) if eta_sec is not None else None,
            "reached": bool(reached)
        })

    return jsonify({
        "bus_id": bus_id,
        "lat": cur_lat,
        "lon": cur_lon,
        "last_idx": last_idx,
        "etas": etas
    })

# ------------------------------
# RUN SERVER (MUST BE LAST)
# ------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
