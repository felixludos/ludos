# Game-Set-Match: An AI-centric framework for turn-based game development

This framework is designed to allow the development of the backends to turn-based games using Python. This includes all the game logic and action generation.
The idea is for the backend to communicate with any frontend (eg. a GUI, an AI player) through JSON objects.

## Short-term goals

1. Complete control flow: Phases, PhaseStack, signals (including errors)
2. Localize gamestate for phase specific information
3. Complete game object handling, including transactions and automatic create/update/remove tables
4. Clean up interface functions and action set syntax
5. Improve logging with html-like tags
6. Formalize config file organization (if necessary)
7. Overhaul test framework (!)

## Long-term goals

1. Develop resilient GameObjects/GamePhases/framework - save code/functionality with data
2. Anonymize GameObject IDs and info - prevent cheating by keeping track of IDs
3. Visual interface language, auto-GUI generator - define config to visualize common GameObject behaviors
4. Develop GSM in Julia for performance improvements
