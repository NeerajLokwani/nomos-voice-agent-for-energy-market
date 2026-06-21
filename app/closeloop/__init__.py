"""Close-the-loop pipeline (ported from the 'norman' build).

Turns an ElevenLabs post-call webhook (transcript + data_collection_results) into
grounded facts -> German note -> email draft -> triggered actions, with a strict
never-fabricate rule. The phone call itself is placed via native ElevenLabs outbound
(app.elevenlabs_client.place_call_via_elevenlabs); this package handles everything
that happens AFTER the call ends.
"""
