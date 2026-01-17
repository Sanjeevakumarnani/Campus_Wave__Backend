import threading
import time
from datetime import datetime
from flask import current_app

def check_and_update_radio_statuses(app):
    """Check and update radio statuses based on current time"""
    with app.app_context():
        try:
            from app.extensions import db
            from app.models.radio import Radio, RadioStatus, HostStatus, MediaType
            from app.models.radio_subscription import RadioSubscription
            from app.models.notification import Notification
            from app.models.live_stream import LiveStream
            
            # Use server local time for comparisons since DB stores naive datetimes
            # IMPORTANT: All comparisons must be consistent with how radios are saved
            now = datetime.now()
            
            # 1. Auto-START: Find UPCOMING radios that should be LIVE
            radios_to_start = Radio.query.filter(
                Radio.status == RadioStatus.UPCOMING,
                Radio.start_time <= now,
                Radio.end_time > now
            ).all()
            
            for radio in radios_to_start:
                # CRITICAL: Logic Ownership - Cannot go LIVE without media
                if not radio.media_url:
                    print(f"[SCHEDULER] SKIPPING auto-start for radio {radio.id}: No media_url found")
                    continue

                print(f"[SCHEDULER] Found radio to start: {radio.title} (ID: {radio.id}, Start: {radio.start_time}, Now: {now})")
                radio.status = RadioStatus.LIVE
                radio.host_status = HostStatus.HOSTING
                
                # IMPORTANT: Preserve existing media_url if set
                if not radio.media_type:
                    radio.media_type = MediaType.AUDIO
                
                radio.stream_started_at = now
                
                # Notify subscribers
                subscribers = RadioSubscription.query.filter_by(radio_id=radio.id).all()
                for sub in subscribers:
                    notification = Notification(
                        user_id=sub.user_id,
                        title=f"📻 {radio.title} is Now Live!",
                        message=f"{radio.title} has started. Join now to listen!",
                        type="RADIO_LIVE",
                        related_id=radio.id
                    )
                    db.session.add(notification)
                
                # CRITICAL: Update Global LiveStream for Student Player
                stream = LiveStream.query.first()
                if not stream:
                    stream = LiveStream(status='ONLINE', started_at=now)
                    db.session.add(stream)
                
                stream.current_audio_id = radio.id
                stream.status = 'ONLINE'
                stream.started_at = now
                stream.title = radio.title
                stream.description = radio.description
                
                print(f"[SCHEDULER] Auto-started radio: {radio.title} and synced to Global Stream")
            
            # 2. Auto-END: Find LIVE radios that should be COMPLETED
            radios_to_end = Radio.query.filter(
                Radio.status == RadioStatus.LIVE,
                Radio.end_time <= now
            ).all()
            
            for radio in radios_to_end:
                print(f"[SCHEDULER] Found radio to end: {radio.title} (ID: {radio.id}, End: {radio.end_time}, Now: {now})")
                radio.status = RadioStatus.COMPLETED
                radio.host_status = HostStatus.ENDED


                # CRITICAL: Clear Global LiveStream if this radio was playing
                stream = LiveStream.query.first()
                if stream and stream.current_audio_id == radio.id:
                    stream.status = 'OFFLINE'
                    stream.current_audio_id = None
                    print(f"[SCHEDULER] Cleared Global Stream for ended radio: {radio.title}")

                print(f"[SCHEDULER] Auto-ended radio: {radio.title}")
            
            # 3. Clean up MISSED radios (UPCOMING but end_time passed)
            radios_missed = Radio.query.filter(
                Radio.status == RadioStatus.UPCOMING,
                Radio.end_time <= now
            ).all()
            
            for radio in radios_missed:
                print(f"[SCHEDULER] Found missed radio: {radio.title} (ID: {radio.id})")
                radio.status = RadioStatus.COMPLETED
                radio.host_status = HostStatus.ENDED
            
            # Commit all changes
            if radios_to_start or radios_to_end or radios_missed:
                db.session.commit()
                print(f"[SCHEDULER] Updated: {len(radios_to_start)} started, {len(radios_to_end)} ended, {len(radios_missed)} missed")
            
        except Exception as e:
            print(f"[SCHEDULER] Error updating statuses: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

def run_scheduler(app):
    """Background thread that runs the scheduler"""
    print("[SCHEDULER] Background scheduler started")
    
    while True:
        try:
            check_and_update_radio_statuses(app)
        except Exception as e:
            print(f"[SCHEDULER] Error in scheduler loop: {str(e)}")
        
        # Wait 10 seconds before next check (reduced from 30 for faster updates)
        time.sleep(10)

def start_background_scheduler(app):
    """Initialize and start the background scheduler thread"""
    scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(app,),
        daemon=True,  # Thread will exit when main program exits
        name="RadioScheduler"
    )
    scheduler_thread.start()
    print("[SCHEDULER] Background scheduler thread initialized")
