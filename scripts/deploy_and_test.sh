#!/usr/bin/env bash
# ============================================================================
# Manual Workflow Guide - Deploy and Test Strategy
# ============================================================================
#
# This file documents the manual steps to deploy and test a strategy.
# Run these commands in order:
#
# ============================================================================
# Step 0 (Optional): Clean backtest server logs
# ============================================================================
# ./scripts/ss_log_manager.sh clean bt
#
# ============================================================================
# Step 1: Restart backtest server
# ============================================================================
# ./scripts/bt_server.sh stop
# sleep 3
# ./scripts/bt_server.sh start
# sleep 3
#
# ============================================================================
# Step 2: Deploy strategy (builds and copies)
# ============================================================================
# ./scripts/deploy_strategy.sh --name <STRATEGY_NAME>
# sleep 2
#
# Example:
# ./scripts/deploy_strategy.sh --name venue_arb
#
# ============================================================================
# Step 3: Terminate all existing instances
# ============================================================================
# ./scripts/run_strategy.sh killall
# sleep 8
#
# ============================================================================
# Step 4: Run full pipeline (recheck → create → backtest)
# ============================================================================
# ./scripts/run_strategy.sh run
#
# This will:
# - Start server (if not running)
# - Recheck strategy DLLs
# - Create strategy instance
# - Start backtest
#
# You can override config values:
# ./scripts/run_strategy.sh run --start 2025-04-01 --end 2025-04-01
#
# ============================================================================
# Step 5 (Optional): Show backtest server logs
# ============================================================================
# ./scripts/ss_logs.sh bt
#
# ============================================================================
# Complete Example Workflow
# ============================================================================
#
# # Clean logs (optional)
# ./scripts/ss_log_manager.sh clean bt
#
# # Restart server
# ./scripts/bt_server.sh stop
# sleep 3
# ./scripts/bt_server.sh start
# sleep 3
#
# # Deploy strategy
# ./scripts/deploy_strategy.sh --name venue_arb
# sleep 2
#
# # Kill all instances
# ./scripts/run_strategy.sh killall
# sleep 8
#
# # Run full pipeline
# ./scripts/run_strategy.sh run
#
# # View logs (optional)
# ./scripts/ss_logs.sh bt
#
# ============================================================================

echo "This script has been replaced with a manual workflow guide."
echo "See the comments in this file for step-by-step instructions."
echo ""
echo "Quick reference:"
echo "  1. ./scripts/bt_server.sh stop && sleep 3 && ./scripts/bt_server.sh start"
echo "  2. ./scripts/deploy_strategy.sh --name <STRATEGY>"
echo "  3. ./scripts/run_strategy.sh killall && sleep 8"
echo "  4. ./scripts/run_strategy.sh run"
echo "  5. ./scripts/ss_logs.sh bt  (optional)"
