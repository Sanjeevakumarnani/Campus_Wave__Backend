import os
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_upload(file, compress_image=False):
    """Save uploaded file and return filename
    
    Args:
        file: FileStorage object from Flask request
        compress_image: If True, compress images to reduce size (JPEG quality 85%)
    
    Returns:
        filename if successful, None otherwise
    """
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Add timestamp to avoid filename conflicts
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        
        # Determine output extension for compressed images
        if compress_image and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            # Convert PNG to JPEG for better compression (unless it has transparency)
            output_ext = ext if ext.lower() in ['.jpg', '.jpeg', '.webp'] else '.jpg'
            filename = f"{name}_{timestamp}{output_ext}"
        else:
            filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        if compress_image and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            try:
                from PIL import Image
                import io
                
                # Read image from file
                img = Image.open(file)
                
                # Convert RGBA to RGB if necessary (for JPEG)
                if img.mode == 'RGBA' and ext.lower() not in ['.png', '.webp']:
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB' and ext.lower() not in ['.png', '.webp']:
                    img = img.convert('RGB')
                
                # Resize if too large (max 1920px on longest side)
                max_size = 1920
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with compression
                if ext.lower() in ['.webp']:
                    img.save(filepath, 'WEBP', quality=85, optimize=True)
                elif ext.lower() in ['.png']:
                    img.save(filepath, 'PNG', optimize=True)
                else:
                    img.save(filepath, 'JPEG', quality=85, optimize=True)
                
                return filename
                
            except Exception as e:
                # Fall back to regular save if compression fails
                print(f"Image compression failed: {e}, saving without compression")
                file.seek(0)  # Reset file pointer
                file.save(filepath)
                return filename
        else:
            file.save(filepath)
            return filename
    return None

def delete_file(filename):
    """Delete uploaded file"""
    if filename:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    return False

