# 🕒 Nerd Clock

### A binary clock for unapologetic nerds

Nerd Clock is a compact RGBW LED‑matrix binary time display with optional HDMI output for visualizing the clock on a screen.  
It’s designed for programmers, makers, tinkerers, and anyone who thinks regular clocks are too mainstream.

---

## ✨ Features

### 🔌 GPIO LED Output

* Supports RGBW LED strings
* Specifically designed for **SK6812** LEDs
* May work for **WS2812** LEDs

### 🖥️ HDMI Display Output

* Visual binary clock matrix
* Optional keyboard shortcuts (when a keyboard is connected)
* Optional text line for extra time‑related info

---

## 📦 What This Version Includes

| Feature Category | Details |
| ---------------- | ------- |
| HDMI Output | Binary matrix, keyboard shortcuts, optional text line |
| LED Output | RGBW support, SK6812‑compatible |
| Platform | Raspberry Pi / SBC‑friendly GPIO design |
| Use Case | Desk clock, wall display, impressing the shit out of colleagues, ambient lighting, etc. |

---

## LED Matrix Layout (5×5 — Seconds Elapsed or Remaining This Year)

The 5×5 LED matrix can display the number of seconds **elapsed** or **remaining** in the current year, counting upward or downward depending on your chosen mode.  
Each LED corresponds to one bit in a 25‑bit binary number:

* `1` = LED on
* `0` = LED off

Although the matrix is shown here in plain binary, the actual clock supports multiple **RGBW color themes**, allowing you to choose how the “on” LEDs appear (white, red, green, blue, or mixed).

### Bit Layout

Bits are arranged left‑to‑right, top‑to‑bottom:

```text
bit 24  bit 23  bit 22  bit 21  bit 20
bit 19  bit 18  bit 17  bit 16  bit 15
bit 14  bit 13  bit 12  bit 11  bit 10
bit 9   bit 8   bit 7   bit 6   bit 5
bit 4   bit 3   bit 2   bit 1   bit 0
```

---

## Example: Binary Value for **1 Second**

Decimal `1` in 25‑bit binary:

```binary
00000 00000 00000 00000 00001
```

Only **bit 0** is on, so the bottom‑right LED is lit.

| 0 | 0 | 0 | 0 | 0 |
| - | - | - | - | - |
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | 0 | 0 | 1 |

---

## 🧵 Wiring

### Wiring (quick reminder for SK6812 chain):
Use 25 individually addressable SK6812 RGB LEDs (or a pre-made 5x5 SK6812 matrix if you can find one).
Chain them in a row-major order (left-to-right, top-to-bottom).

### Connections:
5V → Pi 5V (pin 2/4) or better: external 5V 2-5A supply (share GND!)
GND → Pi GND
Data In of first LED → GPIO 18 (physical pin 12) — hardware PWM pin, best for WS2812/SK6812 leds

Add a 470Ω resistor in series on the data line (good practice).
Add 1000µF capacitor across 5V/GND near the LEDs if using many.

---

## 🚀 Getting Started

### Install Debian Trixie or similar

### Edit startup file in the Debian Terminal:

```cli
nano ~/.config/autostart/nerdclock.desktop
```

contents should be:

```text
[Desktop Entry]
Type=Application
Name=5x5 Binary Nerd Clock
Exec=python3 /home/rob/Binary_Clock/nerd_clock.py
Hidden=false
NoDisplay=false
```

Modify the file as necessary, then hit:
**Ctrl-O**, **enter**, then **Ctrl-X** (save & exit)

---

## 🛠️ Future Enhancements

*Need to fix LED control*
