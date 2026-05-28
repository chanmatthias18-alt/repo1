# Auto Driving Car Simulation

A command-line program that simulates autonomous cars moving on a rectangular grid. Cars follow a sequence of commands and the program detects if any cars collide.

---

## Requirements

- Python 3.9 or higher
- No additional installations required

---

## How to Run

Ensure all files are in the same folder, then open a terminal and navigate to that folder:

```
cd path/to/your/folder
```

### Start the simulation
```
python main.py
```

### Run the tests
```
python test_suite.py
```

---

## Commands

- **N / S / E / W** – North, South, East, West 

- **F** – Move forward one step
- **L** – Turn left 90 degrees
- **R** – Turn right 90 degrees

---

## Example

```
Welcome to Auto Driving Car Simulation!

Please enter the width and height of the simulation field in x y format:
> 10 10

You have created a field of 10 x 10.

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
> 1

Please enter the name of the car:
> A

Please enter initial position of car A in x y Direction format:
> 1 2 N

Please enter the commands for car A:
> FFRFFFFRRL

Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
> 2

Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

After simulation, the result is:
- A, (5,4) S
```

---

## Assumptions

**A1. Field coordinates**
The bottom-left cell is (0,0) and the top-right cell is (width-1, height-1). A 10×10 field has valid positions (0,0) through (9,9).

**A2. Out-of-bounds movement**
If a car tries to move beyond the boundary, the command is silently ignored and the car stays in its current position.

**A3. Collision detection**
Collisions are checked after each car moves. If Car A moves into Car B's cell, both are marked as collided immediately; Car B does not need to move first.

**A4. Collided cars stop**
Once a car collides it stops processing all further commands.

**A5. All cars move at the same speed**
Every car processes exactly one command per step. There is no concept of a faster or slower car.

**A6. No reverse command**
Cars cannot move backwards directly. To move in the opposite direction a car must turn 180 degrees first (LL or RR) then move forward.

---

## Known Gaps & Improvement Areas

**G1. Head-on swap collisions not detected**
If two cars swap positions in the same step (e.g. Car A moves right into where Car B was, and Car B moves left into where Car A was), the program does not detect this as a collision because it only checks where cars end up, not the path they took.

**G2. No validation for overlapping starting positions**
The program does not prevent two cars from being placed at the same starting position. If this happens, their collision behaviour is undefined.

**G3. Collided cars remain on the field**
When two cars collide they freeze in place. The spec does not clarify whether a third car hitting that frozen position should also be considered a collision.

**G4. No exit option on the main menu**
Users cannot exit the program without first running the simulation.

**G5. No way to interrupt a running simulation**
Once the simulation starts, all commands run to completion with no option to pause or stop.

**G6. No UI to visualise the simulation**
Introduce a simple UI for users to visualise the simulation and better understand where the cars are moving and how did they set up the field.
