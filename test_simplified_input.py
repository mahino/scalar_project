#!/usr/bin/env python3
"""
Test script for simplified user input system
"""

import requests
import json

def test_simplified_input():
    """Test the simplified input system"""
    
    # Test Case 1: Simple scenario
    print("=" * 60)
    print("TEST CASE 1: Simple Scenario")
    print("=" * 60)
    
    simplified_input = {
        'services': 2,
        'app_profiles': 1,
        'credentials': 1
    }
    
    print(f"User Input: {simplified_input}")
    print()
    
    # Calculate what the full entity_counts should be
    expected_entity_counts = {
        'spec.resources.app_profile_list': 1,
        'spec.resources.app_profile_list.deployment_create_list': 2,  # = services
        'spec.resources.service_definition_list': 2,
        'spec.resources.substrate_definition_list': 2,  # = app_profiles * services = 1 * 2
        'spec.resources.package_definition_list': 1,   # = app_profiles
        'spec.resources.credential_definition_list': 1
    }
    
    print("Expected Auto-calculations:")
    print(f"  Packages = App Profiles: {expected_entity_counts['spec.resources.package_definition_list']} = {simplified_input['app_profiles']}")
    print(f"  Deployments per Profile = Services: {expected_entity_counts['spec.resources.app_profile_list.deployment_create_list']} = {simplified_input['services']}")
    print(f"  Substrates = App Profiles × Services: {expected_entity_counts['spec.resources.substrate_definition_list']} = {simplified_input['app_profiles']} × {simplified_input['services']}")
    print()
    
    # Test the API with the calculated entity_counts
    api_request = {
        "api_url": "blueprint",
        "entity_counts": expected_entity_counts
    }
    
    try:
        response = requests.post(
            'http://localhost:5001/api/payload/generate',
            headers={'Content-Type': 'application/json'},
            json=api_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify the results
            if 'scaled_payload' in result:
                payload = result['scaled_payload']
                resources = payload.get('spec', {}).get('resources', {})
                
                actual_services = len(resources.get('service_definition_list', []))
                actual_app_profiles = len(resources.get('app_profile_list', []))
                actual_packages = len(resources.get('package_definition_list', []))
                actual_substrates = len(resources.get('substrate_definition_list', []))
                actual_credentials = len(resources.get('credential_definition_list', []))
                
                # Check deployments per profile
                deployments_per_profile = []
                for profile in resources.get('app_profile_list', []):
                    deployments_per_profile.append(len(profile.get('deployment_create_list', [])))
                
                print("RESULTS:")
                print(f"  Services: {actual_services} (expected: {simplified_input['services']})")
                print(f"  App Profiles: {actual_app_profiles} (expected: {simplified_input['app_profiles']})")
                print(f"  Packages: {actual_packages} (expected: {simplified_input['app_profiles']})")
                print(f"  Substrates: {actual_substrates} (expected: {simplified_input['app_profiles'] * simplified_input['services']})")
                print(f"  Credentials: {actual_credentials} (expected: {simplified_input['credentials']})")
                print(f"  Deployments per Profile: {deployments_per_profile} (expected: [{simplified_input['services']}])")
                
                # Check if all rules are satisfied
                rules_satisfied = (
                    actual_services == simplified_input['services'] and
                    actual_app_profiles == simplified_input['app_profiles'] and
                    actual_packages == simplified_input['app_profiles'] and
                    actual_substrates == simplified_input['app_profiles'] * simplified_input['services'] and
                    actual_credentials == simplified_input['credentials'] and
                    all(d == simplified_input['services'] for d in deployments_per_profile)
                )
                
                print()
                print(f"ALL RULES SATISFIED: {'✅ YES' if rules_satisfied else '❌ NO'}")
                
            else:
                print("❌ ERROR: No scaled_payload in response")
                
        else:
            print(f"❌ ERROR: API request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print()
    
    # Test Case 2: Complex scenario
    print("=" * 60)
    print("TEST CASE 2: Complex Scenario")
    print("=" * 60)
    
    simplified_input_2 = {
        'services': 4,
        'app_profiles': 3,
        'credentials': 2
    }
    
    print(f"User Input: {simplified_input_2}")
    print()
    
    expected_entity_counts_2 = {
        'spec.resources.app_profile_list': 3,
        'spec.resources.app_profile_list.deployment_create_list': 4,  # = services
        'spec.resources.service_definition_list': 4,
        'spec.resources.substrate_definition_list': 12,  # = app_profiles * services = 3 * 4
        'spec.resources.package_definition_list': 3,    # = app_profiles
        'spec.resources.credential_definition_list': 2
    }
    
    print("Expected Auto-calculations:")
    print(f"  Packages = App Profiles: {expected_entity_counts_2['spec.resources.package_definition_list']} = {simplified_input_2['app_profiles']}")
    print(f"  Deployments per Profile = Services: {expected_entity_counts_2['spec.resources.app_profile_list.deployment_create_list']} = {simplified_input_2['services']}")
    print(f"  Substrates = App Profiles × Services: {expected_entity_counts_2['spec.resources.substrate_definition_list']} = {simplified_input_2['app_profiles']} × {simplified_input_2['services']}")
    print()
    print("This would result in:")
    print(f"  Total Deployments: {simplified_input_2['app_profiles']} profiles × {simplified_input_2['services']} deployments = {simplified_input_2['app_profiles'] * simplified_input_2['services']} deployments")
    print(f"  Grid Layout: {simplified_input_2['app_profiles'] * simplified_input_2['services']} deployment positions in client_attrs")


if __name__ == '__main__':
    test_simplified_input()
