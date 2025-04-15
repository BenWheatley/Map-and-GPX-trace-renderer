#!/usr/bin/python3

import os
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import xml.etree.ElementTree as ET
import math
from datetime import datetime
import json
from matplotlib.patches import Polygon as MplPolygon
import matplotlib.colors as mcolors
import logging

logger = logging.getLogger(__name__)

def parse_gpx(file_path):
    """Parse GPX file and return list of (lat, lon, time) tuples."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    points = []
    
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        time_elem = trkpt.find('gpx:time', ns)
        if time_elem is not None:
            time = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
            points.append((lat, lon, time))
    return points

def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in kilometers using the Haversine formula."""
    R = 6371.0  # Earth radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def compute_speed_kph(lat1, lon1, lat2, lon2, dt_seconds):
    """Return speed in km/h given two coordinates and time delta in seconds."""
    distance_km = haversine(lat1, lon1, lat2, lon2)
    hours = dt_seconds / 3600.0
    return abs(distance_km / hours) # Care about speed, not velocity, so abs value

def exceeds_speed_threshold(points, max_kph):
    """Check if any segment exceeds max speed in km/h."""
    for i in range(1, len(points)):
        lat1, lon1, t1 = points[i - 1]
        lat2, lon2, t2 = points[i]
        dt_seconds = (t2 - t1).total_seconds()
        if dt_seconds == 0:
            continue
        speed_kph = compute_speed_kph(lat1, lon1, lat2, lon2, dt_seconds)
        if speed_kph > max_kph:
            return True
    return False

def draw_geojson(axies, filepath, fill_color="#00000044", line_color="#00000088"):
    """Load a GeoJSON file and draw its geometries on the given matplotlib axes."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    def rgba(c):
        return mcolors.to_rgba(c)
    
    for feature in data.get('features', []):
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [])
        t = geom.get('type')
        
        if t == 'LineString':
            lons, lats = zip(*coords)
            axies.plot(lons, lats, color=rgba(line_color), linewidth=1, zorder=1)
        
        elif t == 'Polygon':
            for ring in coords:
                lons, lats = zip(*ring)
                axies.add_patch(MplPolygon(list(zip(lons, lats)), closed=True, facecolor=rgba(fill_color), edgecolor=rgba(line_color), linewidth=0.5, zorder=1))
        
        elif t == 'MultiPolygon':
            for polygon in coords:
                for ring in polygon:
                    lons, lats = zip(*ring)
                    axies.add_patch(MplPolygon(list(zip(lons, lats)), closed=True, facecolor=rgba(fill_color), edgecolor=rgba(line_color), linewidth=0.5, zorder=1))

def configure_plot(resolution, bbox):
    """Setup figure, axies"""
    figure, axies = plt.subplots(figsize=(resolution[0] / 100, resolution[1] / 100), dpi=100)
    axies.set_facecolor('white')
    
    if bbox:
        axies.set_xlim(bbox[0], bbox[1])
        axies.set_ylim(bbox[2], bbox[3])
        axies.add_patch(Rectangle((bbox[0], bbox[2]), bbox[1] - bbox[0], bbox[3] - bbox[2], 
                               linewidth=1, edgecolor='black', facecolor='none'))
    
    axies.set_xlabel('Longitude')
    axies.set_ylabel('Latitude')
    
    return (figure, axies)

def draw_geojson_backgrounds(geojson, axies):
    def draw_geojson_backgrounds(geojson, axies):
    """
    Draw one or more GeoJSON files onto the given matplotlib axes with optional fill and line colors.

    Parameters:
        geojson (list of list): Each inner list must contain 1 to 3 elements:
            - [0]: Path to the GeoJSON file.
            - [1] (optional): Fill color as a hex string with alpha (e.g., "#FF000088").
            - [2] (optional): Line color as a hex string with alpha (e.g., "#00000044").
        axies (matplotlib.axes.Axes): The matplotlib axes to draw on.

    Notes:
        - The function supports multiple GeoJSON overlays.
        - Color values should be strings interpretable by `matplotlib.colors.to_rgba`.
        - Geometries supported include Polygon, MultiPolygon, and LineString.

    Example:
        draw_geojson_backgrounds(
            geojson=[
                ["buildings.geojson", "#FF000044", "#000000FF"],
                ["rivers.geojson"]
            ],
            axies=ax
        )
    """
    for path_and_color in geojson:
        if len(path_and_color) == 1:
            draw_geojson(axies, path_and_color[0])
        elif len(path_and_color) == 2:
            draw_geojson(axies, path_and_color[0], path_and_color[1])
        else:
            draw_geojson(axies, path_and_color[0], path_and_color[1], path_and_color[2])

def draw_gpx_points(points, axies):
    lats, lons = zip(*[(p[0], p[1]) for p in points])
    axies.plot(lons, lats, 'k-', linewidth=0.5, zorder=2)

def create_map(source_folder, output_path, resolution, bbox=None, max_speed=None, geojson=None):
    """Plot GPX paths from the folder onto an image."""
    
    figure, axies = configure_plot(resolution=resolution, bbox=bbox)
    
    if geojson:
        draw_geojson_backgrounds(geojson, axies)
    
    for filename in os.listdir(source_folder):
        if filename.endswith('.gpx'):
            file_path = os.path.join(source_folder, filename)
            points = parse_gpx(file_path)
            if max_speed is not None and exceeds_speed_threshold(points, max_speed):
                logger.warning(f"Skipping {filename} (exceeds {max_speed} km/h)")
                continue
            draw_gpx_points(points, axies)
    
    # Save the figure directly to a file
    figure.savefig(output_path, format='png', bbox_inches='tight', pad_inches=0.1)
    plt.close(figure)  # Close the figure to free memory
    
    logger.info(f"Image saved as {output_path}")

def autoscale_resolution_from_bbox(bbox, target_height):
    """Compute resolution from bbox and target height using average latitude."""
    if not bbox or len(bbox) != 4:
        raise ValueError("Bounding box must be provided with four values: min_lon, max_lon, min_lat, max_lat.")
    lat_range = bbox[3] - bbox[2]
    lon_range = bbox[1] - bbox[0]
    scale_factor = math.cos(math.radians((bbox[2] + bbox[3]) / 2))
    aspect_ratio = (lon_range * scale_factor) / lat_range
    width = int(target_height * aspect_ratio)
    return (width, target_height)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Plot GPX paths to an image.')
    parser.add_argument('--source_folder', type=str, help='Path to the folder containing GPX files.')
    parser.add_argument('--output', type=str, default='output.png', help='Output image path.')
    parser.add_argument('--resolution', type=int, nargs=2, default=[512, 512], help='Output image resolution (width height).')
    parser.add_argument('--bbox', type=float, nargs=4, help='Bounding box (min_lon, max_lon, min_lat, max_lat).')
    parser.add_argument('--autoscale', type=int, help='Target image height in pixels. Width is calculated by latitude. Requires --bbox.')
    parser.add_argument('--maxspeed', type=float, help='Exclude GPX tracks that exceed this speed (km/h).')
    parser.add_argument('--geojson', nargs='+', action='append',
                        metavar=('PATH [FILL [LINE]]'),
                        help='Add a GeoJSON overlay with optional color (e.g. "#FF00FF88" (your shell may require the quotes)) for fill and line colours')
    parser.add_argument('--loglevel', default='WARNING', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Set the logging level')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=getattr(logging, args.loglevel))
    
    if args.autoscale:
        resolution = autoscale_resolution_from_bbox(args.bbox, args.autoscale)
    elif args.resolution:
        resolution = tuple(args.resolution)
    
    create_map(args.source_folder, args.output, resolution, args.bbox, args.maxspeed, args.geojson)
