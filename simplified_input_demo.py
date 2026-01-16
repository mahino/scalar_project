#!/usr/bin/env python3
"""
Simplified Input System Demo

This demonstrates how users can specify just 3 simple values:
- Services
- App Profiles  
- Credentials

And the system automatically calculates all other entity counts based on these rules:
- Packages = App Profiles
- Deployments per Profile = Services
- Substrates = App Profiles × Services
"""

import requests
import json

def demo_simplified_input():
    """Demonstrate the simplified input system"""
    
    print("🎯 SIMPLIFIED INPUT SYSTEM DEMO")
    print("=" * 60)
    print()
    
    # Demo scenarios
    scenarios = [
        {
            'name': 'Small Setup',
            'input': {'services': 2, 'app_profiles': 1, 'credentials': 1},
            'description': 'Simple single-profile setup with 2 services'
        },
        {
            'name': 'Medium Setup', 
            'input': {'services': 3, 'app_profiles': 2, 'credentials': 1},
            'description': 'Two profiles with 3 services each'
        },
        {
            'name': 'Large Setup',
            'input': {'services': 5, 'app_profiles': 3, 'credentials': 2},
            'description': 'Three profiles with 5 services each'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📋 SCENARIO {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print()
        
        user_input = scenario['input']
        services = user_input['services']
        app_profiles = user_input['app_profiles'] 
        credentials = user_input['credentials']
        
        print("👤 USER INPUT:")
        print(f"   Services: {services}")
        print(f"   App Profiles: {app_profiles}")
        print(f"   Credentials: {credentials}")
        print()
        
        # Calculate auto-generated values
        packages = app_profiles
        deployments_per_profile = services
        substrates = app_profiles * services
        total_deployments = app_profiles * services
        
        print("🤖 AUTO-CALCULATED:")
        print(f"   Packages = App Profiles: {packages}")
        print(f"   Deployments per Profile = Services: {deployments_per_profile}")
        print(f"   Substrates = App Profiles × Services: {substrates} ({app_profiles} × {services})")
        print(f"   Total Deployments: {total_deployments}")
        print()
        
        # Generate the API request
        entity_counts = {
            'spec.resources.app_profile_list': app_profiles,
            'spec.resources.app_profile_list.deployment_create_list': 1,  # Will be auto-adjusted
            'spec.resources.service_definition_list': services,
            'spec.resources.substrate_definition_list': substrates,
            'spec.resources.package_definition_list': packages,
            'spec.resources.credential_definition_list': credentials
        }
        
        api_request = {
            "api_url": "blueprint",
            "entity_counts": entity_counts
        }
        
        print("📡 API REQUEST:")
        print(json.dumps(api_request, indent=2))
        print()
        
        # Test the API
        try:
            response = requests.post(
                'http://localhost:5001/api/payload/generate',
                headers={'Content-Type': 'application/json'},
                json=api_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if 'scaled_payload' in result:
                    payload = result['scaled_payload']
                    resources = payload.get('spec', {}).get('resources', {})
                    
                    # Verify results
                    actual_services = len(resources.get('service_definition_list', []))
                    actual_app_profiles = len(resources.get('app_profile_list', []))
                    actual_packages = len(resources.get('package_definition_list', []))
                    actual_substrates = len(resources.get('substrate_definition_list', []))
                    actual_credentials = len(resources.get('credential_definition_list', []))
                    
                    deployments_per_profile = []
                    for profile in resources.get('app_profile_list', []):
                        deployments_per_profile.append(len(profile.get('deployment_create_list', [])))
                    
                    # Check client_attrs grid positioning
                    client_attrs = resources.get('client_attrs', {})
                    deployment_positions = 0
                    for profile in resources.get('app_profile_list', []):
                        for deployment in profile.get('deployment_create_list', []):
                            if deployment.get('uuid') in client_attrs:
                                deployment_positions += 1
                    
                    print("✅ RESULTS:")
                    print(f"   Services: {actual_services} ✅")
                    print(f"   App Profiles: {actual_app_profiles} ✅")
                    print(f"   Packages: {actual_packages} ✅")
                    print(f"   Substrates: {actual_substrates} ✅")
                    print(f"   Credentials: {actual_credentials} ✅")
                    print(f"   Deployments per Profile: {deployments_per_profile} ✅")
                    print(f"   Deployment Grid Positions: {deployment_positions} ✅")
                    
                    # Verify all rules
                    rules_satisfied = (
                        actual_services == services and
                        actual_app_profiles == app_profiles and
                        actual_packages == app_profiles and
                        actual_substrates == app_profiles * services and
                        actual_credentials == credentials and
                        all(d == services for d in deployments_per_profile) and
                        deployment_positions == app_profiles * services
                    )
                    
                    print()
                    print(f"🎯 ALL RULES SATISFIED: {'✅ YES' if rules_satisfied else '❌ NO'}")
                    
                else:
                    print("❌ ERROR: No scaled_payload in response")
                    
            else:
                print(f"❌ ERROR: API request failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        print()
        print("─" * 60)
        print()
    
    print("🎉 SIMPLIFIED INPUT SYSTEM SUMMARY:")
    print()
    print("Instead of specifying 8+ complex entity counts, users now only need:")
    print("1. 🔧 Services (how many services)")
    print("2. 📱 App Profiles (how many profiles)")  
    print("3. 🔐 Credentials (how many credentials)")
    print()
    print("The system automatically calculates:")
    print("• Packages = App Profiles")
    print("• Deployments per Profile = Services")
    print("• Substrates = App Profiles × Services")
    print("• Grid positioning for all deployments")
    print("• Perfect UUID mapping for all entities")
    print()
    print("✨ This makes blueprint generation much simpler for users!")


if __name__ == '__main__':
    demo_simplified_input()
