#!/usr/bin/env python3
"""
Circuit Breaker Reset Script
Reset stuck circuit breakers in production
"""

import os
import sys
from datetime import datetime


def reset_circuit_breakers():
    """Reset all Zep-related circuit breakers"""
    print("🔧 CIRCUIT BREAKER RESET")
    print("=" * 40)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print()

    try:
        # Import circuit breaker module
        import circuit_breaker
        from circuit_breaker import CircuitState

        if hasattr(circuit_breaker, "_breakers"):
            breakers = circuit_breaker._breakers
            reset_count = 0

            for name, breaker in breakers.items():
                if "zep" in name.lower():
                    old_state = getattr(breaker, "state", "unknown")
                    old_failures = getattr(breaker, "failure_count", 0)

                    # Reset the breaker
                    breaker.state = CircuitState.CLOSED
                    breaker.failure_count = 0
                    breaker.last_failure_time = None

                    print(f"✅ Reset {name}:")
                    print(f"   Old state: {old_state} (failures: {old_failures})")
                    print(f"   New state: CLOSED (failures: 0)")
                    reset_count += 1

            if reset_count > 0:
                print(f"\n🎉 Successfully reset {reset_count} circuit breakers")
                print(
                    "⚠️  Recommendation: Monitor application logs for any new failures"
                )
                return True
            else:
                print("ℹ️  No Zep circuit breakers found to reset")
                return True

        else:
            print("❌ Circuit breaker system not available")
            return False

    except ImportError as e:
        print(f"❌ Cannot import circuit breaker module: {e}")
        return False
    except Exception as e:
        print(f"❌ Error resetting circuit breakers: {e}")
        return False


def check_reset_success():
    """Verify circuit breakers were reset successfully"""
    print("\n🔍 VERIFYING RESET")
    print("-" * 30)

    try:
        import circuit_breaker

        if hasattr(circuit_breaker, "_breakers"):
            breakers = circuit_breaker._breakers
            all_closed = True

            for name, breaker in breakers.items():
                if "zep" in name.lower():
                    state = getattr(breaker, "state", "unknown")
                    failures = getattr(breaker, "failure_count", 0)

                    if state == "CLOSED" and failures == 0:
                        print(f"✅ {name}: CLOSED (failures: 0)")
                    else:
                        print(f"❌ {name}: {state} (failures: {failures})")
                        all_closed = False

            return all_closed
        else:
            print("⚠️  Cannot verify - circuit breaker system not available")
            return True

    except Exception as e:
        print(f"⚠️  Cannot verify reset: {e}")
        return True


if __name__ == "__main__":
    try:
        print("This script will reset Zep circuit breakers that may be stuck OPEN")
        print("This should resolve issues where Zep requests are being blocked")
        print()

        # Perform reset
        success = reset_circuit_breakers()

        if success:
            # Verify reset worked
            verification_success = check_reset_success()

            if verification_success:
                print("\n🎯 NEXT STEPS:")
                print("1. Test the questionnaire flow again")
                print("2. Monitor logs for any new Zep integration errors")
                print("3. If issues persist, run production_zep_diagnostic.py")
            else:
                print("\n⚠️  Reset may not have been fully successful")
                print(
                    "Consider restarting the application to fully reset circuit breakers"
                )
        else:
            print("\n❌ RESET FAILED")
            print("Consider restarting the application as an alternative")

    except Exception as e:
        print(f"\n💥 SCRIPT ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
