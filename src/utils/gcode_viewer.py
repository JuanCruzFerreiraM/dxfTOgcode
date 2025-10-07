#!/usr/bin/env python3
"""G-code visualization tool with layer-by-layer display and export capabilities.

This module provides functionality to parse and visualize G-code files by layers,
with options to export visualizations as PNG or PDF files.
"""

import re
import sys
import argparse
from collections import defaultdict
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os

MOVE_RE = re.compile(r'^(?:G0|G1)\b', re.IGNORECASE)
COORD_RE = re.compile(r'([XYZ])\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)')


def parse_gcode_moves(path, assume_units='meters'):
    """Parse G-code file and extract movement coordinates.
    
    Args:
        path (str): Path to G-code file
        assume_units (str): Expected units in file ('meters' or 'mm')
        
    Returns:
        list: List of tuples containing (X, Y, Z) coordinates
    """
    moves = []
    cur = {'X': None, 'Y': None, 'Z': None}
    with open(path, 'r') as f:
        for ln in f:
            ln = ln.split(';',1)[0].strip()
            if not ln:
                continue
            if MOVE_RE.search(ln):
                for m in COORD_RE.finditer(ln):
                    axis = m.group(1).upper()
                    val = float(m.group(2))
                    cur[axis] = val
                if cur['X'] is not None or cur['Y'] is not None:
                    moves.append((cur['X'], cur['Y'], cur['Z']))
    return moves


def group_moves_by_layer(moves, z_tol=1e-4):
    """Group movement points by Z-layer within tolerance.
    
    Args:
        moves (list): List of (X, Y, Z) coordinate tuples
        z_tol (float): Tolerance for Z-layer grouping
        
    Returns:
        dict: Dictionary mapping Z-heights to list of line segments
    """
    layers = defaultdict(list)
    prev = (None, None, None)
    for pt in moves:
        x,y,z = pt
        if prev[0] is None:
            prev = pt
            continue
        z_seg = None
        if z is None and prev[2] is None:
            z_seg = 0.0
        elif z is None:
            z_seg = prev[2]
        elif prev[2] is None:
            z_seg = z
        else:
            if abs(z - prev[2]) <= z_tol:
                z_seg = 0.5*(z + prev[2])
            else:
                z_seg = prev[2]
        if prev[0] is not None and prev[1] is not None and x is not None and y is not None:
            layers[round(z_seg,6)].append((prev[0], prev[1], x, y))
        prev = pt
    return dict(layers)

def convert_and_round_segments(segments, to_mm=True, round_01mm=True):
    """Convert coordinate units and round segments for visualization.
    
    Args:
        segments (list): List of line segments as (x1, y1, x2, y2) tuples
        to_mm (bool): Convert from meters to millimeters if True
        round_01mm (bool): Round coordinates to 0.1mm precision if True
        
    Returns:
        list: Processed list of line segments
    """
    out = []
    for (x1,y1,x2,y2) in segments:
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        if to_mm:
            x1 *= 1000.0; y1 *= 1000.0; x2 *= 1000.0; y2 *= 1000.0
        if round_01mm:
            x1 = round(x1, 1); y1 = round(y1, 1); x2 = round(x2, 1); y2 = round(y2, 1)
        if x1 == x2 and y1 == y2:
            continue
        out.append((x1,y1,x2,y2))
    return out


def plot_layer_to_axis(ax, segments):
    """Plot line segments to matplotlib axis.
    
    Args:
        ax (matplotlib.axes.Axes): Matplotlib axis object
        segments (list): List of line segments to plot
    """
    for (x1,y1,x2,y2) in segments:
        ax.plot([x1,x2],[y1,y2], linewidth=0.6)
    ax.set_aspect('equal', 'box')
    ax.set_xticks([])
    ax.set_yticks([])

def save_layer_image(segments, filename, figsize=(4,4), dpi=150, title=None):
    """Save layer visualization as image file.
    
    Args:
        segments (list): List of line segments to visualize
        filename (str): Output filename for image
        figsize (tuple): Figure size as (width, height) inches
        dpi (int): Image resolution in dots per inch
        title (str): Optional title for the plot
    """
    fig, ax = plt.subplots(figsize=figsize)
    plot_layer_to_axis(ax, segments)
    if title:
        ax.set_title(title, fontsize=8)
    plt.tight_layout()
    fig.savefig(filename, dpi=dpi, bbox_inches='tight')
    plt.close(fig)


def save_all_layers_as_png(layers, out_dir, to_mm=True, round_01mm=True, thumb_size=(4,4), dpi=150):
    """Export all layers as individual PNG files.
    
    Args:
        layers (dict): Dictionary mapping Z-heights to segments
        out_dir (str): Output directory for PNG files
        to_mm (bool): Convert coordinates to millimeters
        round_01mm (bool): Round coordinates to 0.1mm precision
        thumb_size (tuple): Image size as (width, height) inches
        dpi (int): Image resolution
    """
    os.makedirs(out_dir, exist_ok=True)
    z_sorted = sorted(layers.keys())
    for i, z in enumerate(z_sorted):
        segs = layers[z]
        segs_conv = convert_and_round_segments(segs, to_mm=to_mm, round_01mm=round_01mm)
        fname = os.path.join(out_dir, f"layer_{i:04d}_z_{z:.6f}.png")
        save_layer_image(segs_conv, fname, figsize=thumb_size, dpi=dpi, title=f"Layer {i} Z={z:.6f}")
        if (i+1) % 50 == 0:
            print(f"Saved {i+1}/{len(z_sorted)} layers...")
    print(f"All layers saved to: {os.path.abspath(out_dir)}")


def save_all_layers_to_pdf(layers, pdf_path, to_mm=True, round_01mm=True, figsize=(6,6), dpi=150):
    """Export all layers to single PDF file.
    
    Args:
        layers (dict): Dictionary mapping Z-heights to segments
        pdf_path (str): Output path for PDF file
        to_mm (bool): Convert coordinates to millimeters
        round_01mm (bool): Round coordinates to 0.1mm precision
        figsize (tuple): Figure size as (width, height) inches
        dpi (int): Image resolution
    """
    z_sorted = sorted(layers.keys())
    with PdfPages(pdf_path) as pdf:
        for i, z in enumerate(z_sorted):
            segs = layers[z]
            segs_conv = convert_and_round_segments(segs, to_mm=to_mm, round_01mm=round_01mm)
            fig, ax = plt.subplots(figsize=figsize)
            plot_layer_to_axis(ax, segs_conv)
            ax.set_title(f"Layer {i} Z={z:.6f}", fontsize=10)
            plt.tight_layout()
            pdf.savefig(fig, dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            if (i+1) % 50 == 0:
                print(f"Añadidas {i+1}/{len(z_sorted)} páginas al PDF...")
    print(f"PDF generado: {os.path.abspath(pdf_path)}")

def main():
    p = argparse.ArgumentParser(description="Visualizador simple de G-code por capas (metros->mm).")
    p.add_argument('file', help='archivo gcode')
    p.add_argument('--list', action='store_true', help='listar capas detectadas y conteos')
    p.add_argument('--show-layer', type=int, default=None, help='mostrar capa por índice (orden ascendente de Z)')
    p.add_argument('--show-all', action='store_true', help='guardar todas las capas (PNG) o PDF según --pdf')
    p.add_argument('--out-dir', default='layers_out', help='directorio para PNGs (usado con --show-all)')
    p.add_argument('--pdf', action='store_true', help='si se usa con --show-all, genera un PDF en vez de PNGs (archivo: out-dir/ALL_LAYERS.pdf)')
    p.add_argument('--z-tol', type=float, default=1e-4, help='tolerancia Z para agrupar capas (en metros)')
    p.add_argument('--no-mm', action='store_true', help='no convertir a mm (mantener unidades originales)')
    p.add_argument('--no-round', action='store_true', help='no redondear a 0.1 mm')
    p.add_argument('--out', default=None, help='guardar imagen de la capa en PNG (cuando se usa --show-layer)')
    p.add_argument('--thumb-size', type=float, nargs=2, default=(4.0,4.0), help='tamaño (inches) de las miniaturas PNG')
    p.add_argument('--pdf-size', type=float, nargs=2, default=(6.0,6.0), help='tamaño (inches) de páginas en PDF')
    args = p.parse_args()

    moves = parse_gcode_moves(args.file, assume_units='meters')
    if not moves:
        print("No se detectaron movimientos G0/G1. Revisa el archivo o adapta el parser.")
        sys.exit(1)

    layers = group_moves_by_layer(moves, z_tol=args.z_tol)
    z_sorted = sorted(layers.keys())

    if args.list:
        print(f"Se detectaron {len(z_sorted)} capas (Z keys):")
        for i,z in enumerate(z_sorted):
            print(f"  [{i}] Z={z:.6f}  segments={len(layers[z])}")

    if args.show_layer is not None:
        if args.show_layer < 0 or args.show_layer >= len(z_sorted):
            print("Índice de capa fuera de rango.")
            sys.exit(1)
        z = z_sorted[args.show_layer]
        segs = layers[z]
        segs_conv = convert_and_round_segments(segs, to_mm=(not args.no_mm), round_01mm=(not args.no_round))
        title = f"{os.path.basename(args.file)}  layer {args.show_layer}  Z={z:.6f} (units: {'mm' if not args.no_mm else 'm'})"
        if args.out:
            save_layer_image(segs_conv, args.out, figsize=tuple(args.thumb_size), title=title)
            print("Guardada:", args.out)
        else:
            # mostrar interactivo breve (usa backend por defecto)
            plt.figure(figsize=(6,6))
            for (x1,y1,x2,y2) in segs_conv:
                plt.plot([x1,x2],[y1,y2], linewidth=0.6)
            plt.gca().set_aspect('equal','box')
            plt.title(title)
            plt.show()

    if args.show_all:
        to_mm = not args.no_mm
        round_01mm = not args.no_round
        if args.pdf:
            os.makedirs(args.out_dir, exist_ok=True)
            pdf_path = os.path.join(args.out_dir, "ALL_LAYERS.pdf")
            save_all_layers_to_pdf(layers, pdf_path, to_mm=to_mm, round_01mm=round_01mm, figsize=tuple(args.pdf_size))
        else:
            save_all_layers_as_png(layers, args.out_dir, to_mm=to_mm, round_01mm=round_01mm, thumb_size=tuple(args.thumb_size))

if __name__ == '__main__':
    main()
