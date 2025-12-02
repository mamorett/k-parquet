import sys
import io
import os
import tempfile
import pandas as pd
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                             QScrollArea, QLabel, QFileDialog, QVBoxLayout, 
                             QDialog, QTextEdit, QHBoxLayout, QProgressBar, 
                             QToolBar, QStyle, QMessageBox, QStatusBar, 
                             QLineEdit, QPushButton, QComboBox, QSlider, QSpinBox)
from PyQt6.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QSettings, QMimeData, QUrl, QPoint
from PyQt6.QtGui import QPixmap, QAction, QColor, QPainter, QDrag, QIcon, QImage


# --- COSTANTI ---
APP_NAME = "Parquet Media Manager 8.0"
ORG_NAME = "KDEUser"

# --- UTILITÀ SICURA PER IMMAGINI ---
def pil_to_pixmap_robust(pil_image):
    try:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        byte_arr = io.BytesIO()
        pil_image.save(byte_arr, format='PNG')
        qpix = QPixmap()
        qpix.loadFromData(byte_arr.getvalue())
        return qpix
    except Exception as e:
        print(f"Errore conversione: {e}")
        return None

# --- WIDGET DRAGGABLE (Nuova Feature) ---
class DraggableImageLabel(QLabel):
    """
    Una Label che permette di trascinare l'immagine fuori dall'applicazione.
    Gestisce sia file reali che immagini binarie (creando file temp).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None # Se esiste un path reale
        self.temp_file = None  # Se dobbiamo creare un temp
        self.setAcceptDrops(False)
        self.drag_start_pos = QPoint()
        # --- IMPOSTAZIONE ICONA (Nativa KDE) ---
        # Prova a cercare icone standard di sistema per visualizzatori immagini
        icon_name = "image-viewer" # Icona standard
        if not QIcon.hasThemeIcon(icon_name):
            icon_name = "applications-graphics" # Fallback
        if not QIcon.hasThemeIcon(icon_name):
            icon_name = "folder-pictures" # Fallback 2
            
        self.setWindowIcon(QIcon.fromTheme(icon_name))        

    def set_content(self, pixmap, path=None):
        self.setPixmap(pixmap)
        self.image_path = path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Se non stiamo premendo il tasto sinistro, ignora
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        # Verifica se l'utente ha mosso il mouse abbastanza da voler iniziare un drag
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        self.start_drag()

    def start_drag(self):
        drag = QDrag(self)
        mime_data = QMimeData()
        
        urls = []
        
        # CASO 1: È un file reale su disco
        if self.image_path and os.path.exists(self.image_path):
            urls.append(QUrl.fromLocalFile(os.path.abspath(self.image_path)))
        
        # CASO 2: È un blob binario nel parquet (nessun file)
        else:
            # Creiamo un file temporaneo per permettere il drop sul Desktop/File Manager
            try:
                # Crea un file temporaneo che non viene cancellato subito
                # Nota: In Linux /tmp viene pulito al riavvio solitamente
                temp_dir = tempfile.gettempdir()
                temp_name = os.path.join(temp_dir, "dragged_image.png")
                self.pixmap().save(temp_name, "PNG")
                urls.append(QUrl.fromLocalFile(temp_name))
            except Exception as e:
                print(f"Errore creazione temp file: {e}")

        # Imposta gli URL (per File Managers)
        if urls:
            mime_data.setUrls(urls)
        
        # Imposta anche l'immagine raw (per Image Editors come GIMP/Krita che supportano incolla diretto)
        mime_data.setImageData(self.pixmap().toImage())

        drag.setMimeData(mime_data)
        
        # Mostra l'immagine mentre la trascini (Ghost image)
        pixmap_preview = self.pixmap().scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio)
        drag.setPixmap(pixmap_preview)
        drag.setHotSpot(QPoint(pixmap_preview.width() // 2, pixmap_preview.height() // 2))

        # Esegui il drag (CopyAction perché non vogliamo cancellare l'originale)
        drag.exec(Qt.DropAction.CopyAction)

# --- WORKER ---
class WorkerSignals(QObject):
    result = pyqtSignal(int, object, object)
    finished = pyqtSignal()

class ImageLoaderWorker(QRunnable):
    def __init__(self, df_slice, start_index, img_col_name, mode='bytes'):
        super().__init__()
        self.df_slice = df_slice
        self.start_index = start_index
        self.img_col_name = img_col_name
        self.mode = mode
        self.signals = WorkerSignals()
        self.is_interrupted = False

    def run(self):
        local_idx = 0
        for i, row in self.df_slice.iterrows():
            if self.is_interrupted: break
            pixmap = self.load_image(row)
            if pixmap:
                self.signals.result.emit(self.start_index + local_idx, pixmap, row)
            local_idx += 1
        self.signals.finished.emit()

    def load_image(self, row):
        try:
            image = None
            raw_val = row[self.img_col_name]

            if self.mode == 'path':
                if isinstance(raw_val, str) and os.path.exists(raw_val):
                    image = Image.open(raw_val)
                else:
                    return self.create_placeholder("File mancante")
            
            elif self.mode == 'bytes':
                b = raw_val['bytes'] if isinstance(raw_val, dict) and 'bytes' in raw_val else raw_val
                if isinstance(b, bytes):
                    image = Image.open(io.BytesIO(b))
            
            if image:
                image.thumbnail((280, 280)) 
                return pil_to_pixmap_robust(image)
        except Exception:
            pass
        return self.create_placeholder("Errore Dati")

    def create_placeholder(self, text):
        pix = QPixmap(260, 260)
        pix.fill(QColor(60, 60, 60))
        painter = QPainter(pix)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return pix

# --- WIDGETS ---
class ImageLabel(QLabel):
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.row_data = row_data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(260, 260)
        self.setStyleSheet("""
            QLabel { border: 1px solid transparent; border-radius: 4px; }
            QLabel:hover { border: 2px solid palette(highlight); background-color: palette(alternateBase); }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().show_details(self.row_data)

class DetailDialog(QDialog):
    def __init__(self, row_data, img_col, mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ispezione Immagine (Drag & Drop abilitato)")
        self.resize(1100, 750)
        
        main_layout = QVBoxLayout(self)

        # Toolbar locale
        actions_layout = QHBoxLayout()
        btn_copy_path = QPushButton("Copia Path")
        btn_copy_path.clicked.connect(lambda: self.copy_to_clip(str(row_data.get(img_col, ""))))
        actions_layout.addWidget(btn_copy_path)

        btn_copy_desc = QPushButton("Copia Descrizione")
        btn_copy_desc.clicked.connect(lambda: self.copy_smart(row_data))
        actions_layout.addWidget(btn_copy_desc)

        actions_layout.addStretch()
        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(self.accept)
        actions_layout.addWidget(btn_close)
        main_layout.addLayout(actions_layout)
        
        # Area Contenuto
        content_layout = QHBoxLayout()
        
        # --- QUI CAMBIA TUTTO: USIAMO IL WIDGET DRAGGABLE ---
        self.img_lbl = DraggableImageLabel() # Nuova classe!
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet("border: 1px solid palette(mid); background-color: palette(base);")
        self.img_lbl.setMinimumWidth(500)
        content_layout.addWidget(self.img_lbl, 2)
        
        # Caricamento SAFE immagine full size
        try:
            val = row_data[img_col]
            img = None
            path_for_drag = None

            if mode == 'path' and isinstance(val, str) and os.path.exists(val):
                img = Image.open(val)
                path_for_drag = val # Salviamo il path per il drag
            elif mode == 'bytes':
                b = val['bytes'] if isinstance(val, dict) else val
                img = Image.open(io.BytesIO(b))
                # path_for_drag rimane None, il widget creerà un temp file
            
            if img:
                pix = pil_to_pixmap_robust(img)
                if pix:
                    scaled = pix.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    # Passiamo sia la pixmap che il path (se c'è) al widget draggable
                    self.img_lbl.set_content(scaled, path_for_drag)
            else:
                self.img_lbl.setText("Immagine non disponibile")
        except Exception as e:
            self.img_lbl.setText(f"Errore: {str(e)}")

        # Metadati
        txt_info = QTextEdit()
        txt_info.setReadOnly(True)
        html = "<table border='0' cellspacing='5' width='100%'>"
        for k, v in row_data.items():
            val_str = str(v)
            bg = "bgcolor='#303030'" if k == img_col else ""
            html += f"<tr><td valign='top'><b>{k}</b></td><td {bg}>{val_str}</td></tr>"
        html += "</table>"
        txt_info.setHtml(html)
        content_layout.addWidget(txt_info, 1)

        main_layout.addLayout(content_layout)

    def copy_to_clip(self, text):
        QApplication.clipboard().setText(text)

    def copy_smart(self, row):
        candidates = ['description', 'caption', 'prompt', 'text', 'alt_text']
        for c in candidates:
            if c in row:
                QApplication.clipboard().setText(str(row[c]))
                return
        QApplication.clipboard().setText(str(row.to_dict()))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG_NAME, APP_NAME)
        
        geom = self.settings.value("geometry")
        if geom: self.restoreGeometry(geom)
        else: self.resize(1300, 900)
        
        self.setWindowTitle(APP_NAME)
        self.threadpool = QThreadPool()
        
        self.df_full = None      
        self.df_current = None   
        
        self.img_col = None
        self.load_mode = 'bytes'
        self.page_size = 50
        self.current_page = 0
        self.total_pages = 0

        self.init_ui()
        
        last_file = self.settings.value("last_file")
        if last_file and isinstance(last_file, str) and os.path.exists(last_file):
            self.load_parquet(last_file)

    def init_ui(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        style = self.style()
        act_open = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Apri", self)
        act_open.triggered.connect(self.open_file_dialog)
        toolbar.addAction(act_open)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Ordina: "))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Default", "Nome File (A-Z)", "Data Recente"])
        self.combo_sort.currentIndexChanged.connect(self.apply_sort)
        toolbar.addWidget(self.combo_sort)
        toolbar.addSeparator()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca...")
        self.search_bar.setFixedWidth(200)
        self.search_bar.returnPressed.connect(self.perform_search)
        toolbar.addWidget(self.search_bar)
        
        btn_search = QPushButton("Vai")
        btn_search.clicked.connect(self.perform_search)
        toolbar.addWidget(btn_search)

        # Bottom Bar
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.btn_prev.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.btn_prev)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 1)
        self.slider.sliderReleased.connect(self.on_slider_release) 
        self.slider.valueChanged.connect(self.on_slider_drag)      
        nav_layout.addWidget(self.slider)

        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, 1)
        self.spin_page.setKeyboardTracking(False)
        self.spin_page.editingFinished.connect(self.on_spin_change)
        nav_layout.addWidget(self.spin_page)

        self.lbl_total = QLabel(" / 1")
        nav_layout.addWidget(self.lbl_total)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.btn_next.clicked.connect(self.next_page)
        nav_layout.addWidget(self.btn_next)

        bottom_toolbar = QToolBar("Nav")
        bottom_toolbar.setMovable(False)
        bottom_toolbar.addWidget(nav_widget)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, bottom_toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(10)
        self.scroll.setWidget(self.grid_container)
        self.setCentralWidget(self.scroll)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(200)
        self.progress.setVisible(False)
        self.status.addPermanentWidget(self.progress)

    def update_pagination_controls(self):
        if self.total_pages == 0: return
        self.slider.blockSignals(True)
        self.spin_page.blockSignals(True)
        self.slider.setRange(1, self.total_pages)
        self.slider.setValue(self.current_page)
        self.spin_page.setRange(1, self.total_pages)
        self.spin_page.setValue(self.current_page)
        self.lbl_total.setText(f" / {self.total_pages} (Tot: {len(self.df_current)})")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)
        self.slider.blockSignals(False)
        self.spin_page.blockSignals(False)

    def on_slider_drag(self, val):
        self.spin_page.blockSignals(True)
        self.spin_page.setValue(val)
        self.spin_page.blockSignals(False)

    def on_slider_release(self):
        target_page = self.slider.value()
        if target_page != self.current_page: self.load_page(target_page)

    def on_spin_change(self):
        target_page = self.spin_page.value()
        if target_page != self.current_page: self.load_page(target_page)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "Apri Parquet", str(last_dir), "Parquet (*.parquet);;All (*)")
        if path:
            self.settings.setValue("last_dir", os.path.dirname(path))
            self.load_parquet(path)

    def load_parquet(self, path):
        self.status.showMessage(f"Lettura: {path}...")
        QApplication.processEvents()
        try:
            self.df_full = pd.read_parquet(path)
            self.df_current = self.df_full
            self.img_col = None
            self.load_mode = 'bytes'
            
            for col in self.df_full.columns:
                if "path" in col.lower() or "file" in col.lower():
                    val = self.df_full[col].dropna().iloc[0] if not self.df_full[col].empty else None
                    if isinstance(val, str) and (val.lower().endswith(('.jpg', '.png', '.webp'))):
                        self.img_col = col
                        self.load_mode = 'path'
                        break
            if not self.img_col:
                for col in self.df_full.columns:
                    val = self.df_full[col].iloc[0]
                    if (isinstance(val, dict) and 'bytes' in val) or isinstance(val, bytes):
                        self.img_col = col
                        self.load_mode = 'bytes'
                        break
            if not self.img_col and 'image_path' in self.df_full.columns:
                 self.img_col = 'image_path'
                 self.load_mode = 'path'

            if not self.img_col:
                QMessageBox.critical(self, "Errore", "Nessuna colonna immagine trovata.")
                return

            self.settings.setValue("last_file", path)
            self.search_bar.clear()
            self.update_pagination_state()
            self.load_page(1)
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))
            self.status.showMessage("Errore caricamento.")

    def apply_sort(self, index):
        if self.df_current is None or self.df_current.empty: return
        criteria = self.combo_sort.itemText(index)
        try:
            if "Nome File" in criteria and self.img_col:
                self.df_current = self.df_current.sort_values(by=self.img_col, ascending=True)
            elif "Data Recente" in criteria:
                col = next((c for c in ['created_at', 'modified_at', 'timestamp'] if c in self.df_current.columns), None)
                if col: self.df_current = self.df_current.sort_values(by=col, ascending=False)
            self.load_page(1)
        except Exception: pass

    def perform_search(self):
        if self.df_full is None: return
        query = self.search_bar.text().strip().lower()
        if not query:
            self.df_current = self.df_full
        else:
            mask = self.df_full.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
            self.df_current = self.df_full[mask]
        self.update_pagination_state()
        self.load_page(1)

    def update_pagination_state(self):
        if self.df_current is None: return
        total_rows = len(self.df_current)
        self.total_pages = (total_rows // self.page_size) + (1 if total_rows % self.page_size > 0 else 0)
        if self.total_pages == 0: self.total_pages = 1
        self.update_pagination_controls()

    def load_page(self, page_num):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

        if self.df_current.empty: return

        self.current_page = page_num
        self.update_pagination_controls()
        
        start = (page_num - 1) * self.page_size
        end = start + self.page_size
        df_slice = self.df_current.iloc[start:end]

        self.progress.setVisible(True)
        self.progress.setRange(0, len(df_slice))
        self.progress.setValue(0)
        
        worker = ImageLoaderWorker(df_slice, start, self.img_col, self.load_mode)
        worker.signals.result.connect(self.add_item)
        worker.signals.finished.connect(lambda: self.progress.setVisible(False))
        self.threadpool.start(worker)

    def add_item(self, idx, pixmap, row):
        relative_idx = idx % self.page_size
        r, c = divmod(relative_idx, 5)
        lbl = ImageLabel(row, self)
        lbl.setPixmap(pixmap)
        lbl.setToolTip(f"{row.get(self.img_col, '')}")
        self.grid.addWidget(lbl, r, c)
        self.progress.setValue(self.progress.value() + 1)

    def prev_page(self):
        if self.current_page > 1: self.load_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages: self.load_page(self.current_page + 1)
    
    def show_details(self, row):
        dlg = DetailDialog(row, self.img_col, self.load_mode, self)
        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Imposta ID applicazione per Wayland/KDE (così raggruppa le finestre e mostra l'icona giusta)
    app.setDesktopFileName("parquet.viewer.app") 
    
    # Imposta l'icona globale dell'app usando il tema di sistema
    app_icon = QIcon.fromTheme("image-viewer")
    if app_icon.isNull():
        app_icon = QIcon.fromTheme("applications-graphics")
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())