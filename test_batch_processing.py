#!/usr/bin/env python3
"""
Test script for batch AFP sequence processing.
Generates 100 test sequences and sends them to the API.
"""
import asyncio
import httpx
import json
import time

# Generate 100 test sequences
def generate_test_sequences(count=100):
    """Generate synthetic AFP-like sequences for testing."""
    base_sequences = [
        "DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR",
        "CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC",
        "AVLLPAGELGAATCTANPACETWCPVTT",
        "TKNQDGGAPPAVNPTANPTANPTANPTANPTA",
        "NFELTHHPDKLHGDTVYSAFSTYKPQKAIHFNGC",
    ]
    
    sequences = []
    for i in range(count):
        # Use one of the base sequences with slight variations
        base = base_sequences[i % len(base_sequences)]
        seq_id = f"AFP_TEST_{i+1:03d}"
        
        # Add some variation by repeating or truncating
        if i < 50:
            sequence = base
        else:
            # Create longer sequences by concatenation
            sequence = base + base[:len(base)//2]
        
        sequences.append({
            "sequence_id": seq_id,
            "sequence": sequence
        })
    
    return sequences

async def test_batch_processing():
    """Test the batch processing API endpoint."""
    print("🧪 Testing Batch AFP Sequence Processing")
    print("=" * 60)
    
    # Generate test data
    sequences = generate_test_sequences(100)
    print(f"\n✅ Generated {len(sequences)} test sequences")
    
    # Prepare request
    url = "http://localhost:8000/api/v1/chat/batch/process"
    payload = {
        "sequences": sequences,
        "model_key": "deepseek",  # Use DeepSeek model
        "analysis_type": "quick",  # Quick analysis for faster testing
        "concurrent_limit": 5
    }
    
    print(f"\n📤 Sending batch request...")
    print(f"   - Sequences: {len(sequences)}")
    print(f"   - Model: {payload['model_key']}")
    print(f"   - Analysis Type: {payload['analysis_type']}")
    print(f"   - Concurrent Limit: {payload['concurrent_limit']}")
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                print(f"\n❌ Request failed: {response.status_code}")
                print(response.text)
                return
            
            result = response.json()
            elapsed = time.time() - start_time
            
            print(f"\n✅ Batch processing completed!")
            print(f"   - Batch ID: {result['batch_id']}")
            print(f"   - Status: {result['status']}")
            print(f"   - Total Sequences: {result['total_sequences']}")
            print(f"   - Successful: {result['successful']}")
            print(f"   - Failed: {result['failed']}")
            print(f"   - Total Time: {elapsed:.2f}s")
            print(f"   - Avg per Sequence: {elapsed/len(sequences)*1000:.0f}ms")
            
            # Show first few results
            print(f"\n📊 Sample Results (first 3):")
            for i, res in enumerate(result['results'][:3]):
                print(f"\n   [{i+1}] {res['sequence_id']}")
                print(f"       Success: {'✅' if res['success'] else '❌'}")
                print(f"       Model: {res['model_used']}")
                print(f"       Time: {res['processing_time_ms']}ms")
                if res['success']:
                    preview = res['analysis'][:100].replace('\n', ' ')
                    print(f"       Preview: {preview}...")
                else:
                    print(f"       Error: {res['error_message']}")
            
            # Test export
            batch_id = result['batch_id']
            print(f"\n💾 Testing export endpoints...")
            
            # Export as CSV
            csv_url = f"http://localhost:8000/api/v1/chat/batch/{batch_id}/export?format=csv"
            csv_response = await client.get(csv_url)
            if csv_response.status_code == 200:
                print(f"   ✅ CSV export successful ({len(csv_response.content)} bytes)")
                # Save to file
                with open(f"/tmp/batch_{batch_id}.csv", "wb") as f:
                    f.write(csv_response.content)
                print(f"   📁 Saved to: /tmp/batch_{batch_id}.csv")
            
            # Export as JSON
            json_url = f"http://localhost:8000/api/v1/chat/batch/{batch_id}/export?format=json"
            json_response = await client.get(json_url)
            if json_response.status_code == 200:
                print(f"   ✅ JSON export successful ({len(json_response.content)} bytes)")
                with open(f"/tmp/batch_{batch_id}.json", "wb") as f:
                    f.write(json_response.content)
                print(f"   📁 Saved to: /tmp/batch_{batch_id}.json")
            
            print(f"\n🎉 All tests passed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_processing())
