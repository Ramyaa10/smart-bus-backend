import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

void main() {
  runApp(const BusTrackerApp());
}

class BusTrackerApp extends StatelessWidget {
  const BusTrackerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Smart Bus Tracker',
      theme: ThemeData(primarySwatch: Colors.indigo),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final String baseUrl = "http://192.168.101.241:5000"; // your backend IP
  Map<String, dynamic> busA = {};
  Map<String, dynamic> busB = {};
  bool loading = true;

  @override
  void initState() {
    super.initState();
    fetchBusData();

    // 🔁 Auto-refresh every 10 seconds
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 10));
      if (!mounted) return false; // stop if user leaves
      await fetchBusData();
      return true; // repeat
    });
  }

  Future<void> fetchBusData() async {
    try {
      final aResponse = await http.get(Uri.parse("$baseUrl/bus/BusA"));
      final bResponse = await http.get(Uri.parse("$baseUrl/bus/BusB"));

      if (aResponse.statusCode == 200 && bResponse.statusCode == 200) {
        setState(() {
          busA = json.decode(aResponse.body);
          busB = json.decode(bResponse.body);
          loading = false;
        });
      } else {
        debugPrint("⚠️ Error: Could not fetch bus data");
      }
    } catch (e) {
      debugPrint("❌ Error fetching data: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Smart Bus Tracker")),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: fetchBusData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  buildBusCard("BusA", busA),
                  const SizedBox(height: 16),
                  buildBusCard("BusB", busB),
                ],
              ),
            ),
    );
  }

  Widget buildBusCard(String busId, Map<String, dynamic> data) {
    return Card(
      elevation: 5,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("${data['name'] ?? busId}",
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text("Available Seats: ${data['available_seats'] ?? 'N/A'}"),
            Text("Total Seats: ${data['total_seats'] ?? 'N/A'}"),
            const SizedBox(height: 15),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => TrackPage(busId: busId, busName: data['name']),
                      ),
                    );
                  },
                  icon: const Icon(Icons.location_on),
                  label: const Text("Track"),
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => InfoPage(busId: busId, busName: data['name']),
                      ),
                    );
                  },
                  icon: const Icon(Icons.info),
                  label: const Text("Information"),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}


//////////////////////////////////////////////////////////////////
// 🧭 INFO PAGE – Shows live ETA & stop status
//////////////////////////////////////////////////////////////////
class InfoPage extends StatefulWidget {
  final String busId;
  final String busName;
  const InfoPage({super.key, required this.busId, required this.busName});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {
  final String baseUrl = "http://192.168.101.241:5000";
  List<dynamic> etas = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    fetchLive();
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 10));
      if (!mounted) return false;
      await fetchLive();
      return true;
    });
  }

  Future<void> fetchLive() async {
    try {
      final res = await http.get(Uri.parse("$baseUrl/live_status/${widget.busId}"));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        setState(() {
          etas = data["etas"];
          loading = false;
        });
      }
    } catch (e) {
      debugPrint("Error fetching live: $e");
    }
  }

  String prettyEta(int? etaSec) {
    if (etaSec == null) return "--";
    if (etaSec <= 0) return "—";
    final minutes = etaSec ~/ 60;
    final seconds = etaSec % 60;
    if (minutes >= 60) {
      final hr = minutes ~/ 60;
      final m = minutes % 60;
      return "${hr}h ${m}m";
    } else if (minutes > 0) {
      return "${minutes}m ${seconds}s";
    } else {
      return "${seconds}s";
    }
  }

  String prettyDistance(int meters) {
    if (meters < 1000) return "${meters} m";
    final km = meters / 1000.0;
    return "${km.toStringAsFixed(2)} km";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("${widget.busName} — Live Info")),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  color: Colors.indigo.shade50,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(widget.busName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      ElevatedButton.icon(
                        onPressed: () {
                          Navigator.push(context, MaterialPageRoute(builder: (_) => TrackPage(busId: widget.busId, busName: widget.busName)));
                        },
                        icon: const Icon(Icons.map),
                        label: const Text("Track"),
                      )
                    ],
                  ),
                ),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: fetchLive,
                    child: ListView.builder(
                      itemCount: etas.length,
                      itemBuilder: (context, index) {
                        final s = etas[index];
                        final stopName = s["stop"] ?? "Unknown";
                        final reached = s["reached"] == true;
                        final distance = s["distance_m"] ?? 0;
                        final etaSec = s["eta_sec"] ?? 0;

                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          elevation: 2,
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: reached ? Colors.green : Colors.indigo,
                              child: Icon(reached ? Icons.check : Icons.directions_bus, color: Colors.white),
                            ),
                            title: Text(stopName, style: TextStyle(fontWeight: reached ? FontWeight.bold : FontWeight.normal)),
                            subtitle: reached
                                ? Text("✅ Bus has passed $stopName", style: const TextStyle(color: Colors.green))
                                : Text("${prettyEta(etaSec)} • ${prettyDistance(distance)}"),
                            trailing: reached ? const Icon(Icons.check_circle, color: Colors.green) : null,
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}


//////////////////////////////////////////////////////////////////
// 🗺️ TRACK PAGE – Live map with moving bus marker (for flutter_map 8.x)
//////////////////////////////////////////////////////////////////
class TrackPage extends StatefulWidget {
  final String busId;
  final String busName;
  const TrackPage({super.key, required this.busId, required this.busName});

  @override
  State<TrackPage> createState() => _TrackPageState();
}

class _TrackPageState extends State<TrackPage> {
  final String baseUrl = "http://192.168.101.241:5000";
  double lat = 12.93, lon = 79.13;
  late final MapController mapController = MapController();
  double zoomLevel = 14.0;
  List<LatLng> polylinePoints = [];
  List<dynamic> stops = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    // get route stops once (buses endpoint gives static stops)
    fetchRouteStops();
    fetchPosition();
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 5));
      if (!mounted) return false;
      await fetchPosition();
      return true;
    });
  }

  Future<void> fetchRouteStops() async {
  try {
    final res = await http.get(Uri.parse("$baseUrl/bus/${widget.busId}"));
    if (res.statusCode == 200) {
      // Fetch full route (coordinates) for polyline
      final live = await http.get(Uri.parse("$baseUrl/live_status/${widget.busId}"));
      if (live.statusCode == 200) {
        final liveJson = json.decode(live.body);
        final etas = liveJson["etas"] as List<dynamic>;
        setState(() {
          polylinePoints = [
            for (var e in etas)
              if (e.containsKey("lat") && e.containsKey("lon"))
                LatLng((e["lat"] as num).toDouble(), (e["lon"] as num).toDouble())
          ];
          stops = etas;
          loading = false;
        });
      }
    }
  } catch (e) {
    debugPrint("Error fetching route stops: $e");
  }
}


  Future<void> fetchPosition() async {
    try {
      final res = await http.get(Uri.parse("$baseUrl/live_status/${widget.busId}"));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        setState(() {
          lat = (data["lat"] as num).toDouble();
          lon = (data["lon"] as num).toDouble();
          // build polyline and stop markers from returned route positions if backend includes them (recommended)
          final etas = data["etas"] as List<dynamic>;
          polylinePoints = [];
          stops = etas;
          for (var e in etas) {
            // backend: we returned only stop name, distance, idx, eta, reached.
            // If your backend also returns route coords per stop, use them:
            if (e.containsKey("lat") && e.containsKey("lon")) {
              polylinePoints.add(LatLng((e["lat"] as num).toDouble(), (e["lon"] as num).toDouble()));
            } else {
              // fallback: keep current bus position to avoid crash
            }
          }
        });
        // center map to current bus location
        mapController.move(LatLng(lat, lon), zoomLevel);
      }
    } catch (e) {
      debugPrint("Error fetching position: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    final cur = LatLng(lat, lon);
    return Scaffold(
      appBar: AppBar(title: Text("Tracking - ${widget.busName}")),
      body: loading ? const Center(child: CircularProgressIndicator()) : FlutterMap(
        mapController: mapController,
        options: MapOptions(
          initialCenter: cur,
          initialZoom: zoomLevel,
          interactionOptions: const InteractionOptions(flags: InteractiveFlag.all),
        ),
        children: [
          TileLayer(urlTemplate: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", userAgentPackageName: 'com.example.bus_tracker_app'),
          if (polylinePoints.isNotEmpty)
            PolylineLayer(polylines: [
              Polyline(points: polylinePoints, strokeWidth: 4.0, color: Colors.blueAccent),
            ]),
          MarkerLayer(markers: [
            // bus marker
            Marker(point: cur, width: 60, height: 60, child: const Icon(Icons.directions_bus, color: Colors.red, size: 36)),
            // stop markers
            for (var s in stops)
              if (s.containsKey("lat") && s.containsKey("lon"))
                Marker(
                    point: LatLng((s["lat"] as num).toDouble(), (s["lon"] as num).toDouble()),
                    width: 40,
                    height: 40,
                    child: Icon(Icons.location_on, color: s["reached"] ? Colors.green : Colors.indigo))
          ]),
        ],
      ),
    );
  }
}


