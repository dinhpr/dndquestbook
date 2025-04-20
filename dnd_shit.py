import pygame
import threading
import sys
import configparser
import requests
import time
import hashlib
import pygame.mixer
from pathlib import Path

# Constants
WINDOW_SIZE = (1000, 1000)
COLORS = {
    "text": (255, 255, 255),
    "completed": (127, 133, 32),
    "failed": (84, 84, 84),
    "in_progress": (51, 253, 255),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "gray": (84, 84, 84),
    "button_border": (255, 255, 0),
    "button_bg": (0, 0, 0)
}

FONT_SIZES = {
    "header": 95,
    "category": 50,
    "title": 36,
    "description": 24,
    "step": 24,
    "rewards": 24,
    "after_completion": 36
}

SCROLL_SPEED = 80
MENU_TOP = 182
MENU_BOTTOM = 924

class ResourceManager:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.data_path = self.base_path / "data"
        self.questlog_path = self.base_path / "questlog.ini"
        self.last_hash = None  # Сохраняем хэш только в памяти

        if not self.data_path.exists():
            self.data_path.mkdir()

    def download_questlog(self):
        try:
            with open(self.data_path / "servername", "r", encoding="utf-8") as f:
                url = f.read().strip()

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Хэш нового содержимого
            new_hash = hashlib.sha256(response.content).hexdigest()

            # Сохраняем файл
            with open(self.questlog_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            # Проверка изменения
            if self.last_hash is not None and new_hash != self.last_hash:
                self.play_update_sound()

            self.last_hash = new_hash  # Обновляем хэш в памяти
            return True

        except Exception as e:
            print(f"Error downloading questlog: {e}")
            return False

    def play_update_sound(self):
        try:
            pygame.mixer.init()
            sound = pygame.mixer.Sound(str(self.data_path / "update.ogg"))
            sound.play()
        except Exception as e:
            print(f"Error playing update sound: {e}")

class QuestManager:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.quests = []
        self.hidden_categories = set()

    def get_category_status(self, category):
        category_quests = [q for q in self.quests if q["category"] == category]
        if all(self.get_quest_status(q) == "completed" for q in category_quests):
            return "completed"
        elif all(self.get_quest_status(q) == "failed" for q in category_quests):
            return "failed"
        return "in_progress"

    def load_quests(self):
        self.hidden_categories.clear()
        config = configparser.ConfigParser()
        
        try:
            config.read(self.resource_manager.questlog_path, encoding="utf-8")
        except FileNotFoundError:
            return

        self.quests = []
        for section in config.sections():
            category = config.get(section, "category", fallback="").strip()
            if "*" in category:
                self.hidden_categories.add(category.replace("*", "").strip())
                continue
            
            steps = []
            for step in config.get(section, "steps", fallback="").split(","):
                step = step.strip()
                if not step or "*" in step: continue
                try:
                    text, status = step.split(":", 1)
                    steps.append({"text": text.strip(), "status": int(status)})
                except ValueError:
                    continue
            
            self.quests.append({
                "name": section,
                "category": category,
                "description": config.get(section, "description", fallback=""),
                "steps": steps,
                "rewards": [r.strip() for r in config.get(section, "rewards", fallback="").split(",") if r.strip()]
            })

    def load_quests_async(self, qm):
        def task():
            if qm.resource_manager.download_questlog():
                            qm.load_quests()
        threading.Thread(target=task, daemon=True).start()

    
    def get_quest_status(self, quest):
        if all(step["status"] == 1 for step in quest["steps"]):
            return "completed"
        if all(step["status"] == -1 for step in quest["steps"]):
            return "failed"
        return "in_progress"

class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Fynn's spellbook")
        
        self.resources = self.load_resources()
        self.fonts = self.load_fonts()
        self.scroll_offset = 0
        self.clip_rect = pygame.Rect(0, MENU_TOP, WINDOW_SIZE[0], MENU_BOTTOM - MENU_TOP)

    def load_resources(self):
        res_mgr = ResourceManager()
        return {
            "background": pygame.image.load(res_mgr.data_path / "background.png").convert(),
            "menu": pygame.image.load(res_mgr.data_path / "menu.png").convert_alpha(),
            "icon": pygame.image.load(res_mgr.data_path / "icon.png")
        }

    def load_fonts(self):
        res_mgr = ResourceManager()
        fonts = {}
        for name, size in FONT_SIZES.items():
            fonts[name] = pygame.font.Font(res_mgr.data_path / "determinationmonorusbylyajk.otf", size)
        fonts["symbol"] = pygame.font.Font(res_mgr.data_path / "symbols_font.otf", 24)
        return fonts

    def render_text_block(self, content_surface, text, font_type, color, pos, max_width, max_height):
        font = self.fonts[font_type]
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        y = pos[1]
        for line in lines:
            if y + font.get_height() > pos[1] + max_height:
                break
            text_surf = font.render(line, True, color)
            content_surface.blit(text_surf, (pos[0], y))
            y += font.get_height()
        return y

    def render_quest(self, content_surface, surface, quest, y_pos, quest_manager):
        category_status = quest_manager.get_category_status(quest["category"])
        quest_status = quest_manager.get_quest_status(quest)
        
        # Render category
        if quest["category"] != self.last_category:
            self.last_category = quest["category"]
            category_text = quest["category"]
            if category_status != "in_progress":
                category_text += f" ({'выполнено' if category_status == 'completed' else 'провалено'})"
            
            category_color = COLORS["completed"] if category_status == "completed" else \
                           COLORS["failed"] if category_status == "failed" else COLORS["yellow"]
            
            category_surf = self.fonts["category"].render(category_text, True, category_color)
            surface.blit(category_surf, (104, y_pos))
            y_pos += 60
        
        if category_status in ("completed", "failed"):
            return y_pos
        
        # Render quest title
        quest_color = COLORS["completed"] if quest_status == "completed" else \
                    COLORS["failed"] if quest_status == "failed" else COLORS["in_progress"]
        
        title_text = quest["name"]
        if quest_status != "in_progress":
            title_text += f" ({'выполнено' if quest_status == 'completed' else 'провалено'})"
        
        title_surf = self.fonts["title"].render(title_text, True, quest_color)
        surface.blit(title_surf, (143, y_pos))
        y_pos += 40
        
        if quest_status != "in_progress":
            return y_pos
        
        # Render description
        y_pos = self.render_text_block(content_surface,
            quest["description"], "description", COLORS["text"],
            (143, y_pos), 699, 85
        ) + 10
        
        # Render steps
        for step in quest["steps"]:
            symbol = "[!]" if step["status"] == 0 else "[V]" if step["status"] == 1 else "[X]"
            symbol_color = COLORS["yellow"] if step["status"] == 0 else \
                          COLORS["green"] if step["status"] == 1 else COLORS["gray"]
            
            symbol_surf = self.fonts["symbol"].render(symbol, True, symbol_color)
            step_surf = self.fonts["step"].render(f" {step['text']}", True, COLORS["text"])
            surface.blit(symbol_surf, (143, y_pos))
            surface.blit(step_surf, (173, y_pos))
            y_pos += 30
        
        # Render rewards
        if quest["rewards"]:
            reward_header = self.fonts["after_completion"].render("После выполнения:", True, COLORS["text"])
            surface.blit(reward_header, (143, y_pos))
            y_pos += 40
            
            for reward in quest["rewards"]:
                reward_surf = self.fonts["rewards"].render(f"* {reward}", True, COLORS["text"])
                surface.blit(reward_surf, (143, y_pos))
                y_pos += 30
        
        return y_pos

    def draw_refresh_button(self):
        button_rect = pygame.Rect(WINDOW_SIZE[0]-160, WINDOW_SIZE[1]-50, 155, 45)
        pygame.draw.rect(self.screen, COLORS["button_bg"], button_rect)
        pygame.draw.rect(self.screen, COLORS["button_border"], button_rect, 2)
        text_surf = self.fonts["title"].render("Обновить", True, COLORS["yellow"])
        text_rect = text_surf.get_rect(center=button_rect.center)
        self.screen.blit(text_surf, text_rect)
        return button_rect

    def main_loop(self, quest_manager):
        TIMER_DURATION = 5  # seconds
        start_time = time.time()
        quest_loaded = False

        
        clock = pygame.time.Clock()
        pygame.display.set_icon(self.resources["icon"])
        
        # Загружаем и подготавливаем изображения
        background = self.resources["background"]
        menu = self.resources["menu"]
        menu_rect = menu.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2))

        while True:
            # Обработка событий
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4: 
                        self.scroll_offset = max(self.scroll_offset - SCROLL_SPEED, 0)
                    elif event.button == 5: 
                        self.scroll_offset += SCROLL_SPEED
                    
                    if self.draw_refresh_button().collidepoint(event.pos):
                        quest_manager.load_quests_async(quest_manager)

            # Рендеринг фона
            self.screen.blit(background, (0, 0))
            self.screen.blit(menu, menu_rect)
            
            # Создаем поверхность для обрезаемого контента
            content_surface = pygame.Surface((WINDOW_SIZE[0], WINDOW_SIZE[1]), pygame.SRCALPHA)
            
            # Заголовок
            header_surf = self.fonts["header"].render("Квесты", True, COLORS["text"])
            self.screen.blit(header_surf, (108, 98))
            
            # Рендерим квесты
            y_pos = 175 - self.scroll_offset
            self.last_category = None
            for quest in quest_manager.quests:
                if quest["category"] in quest_manager.hidden_categories:
                    continue
                
                y_pos = self.render_quest(content_surface, content_surface, quest, y_pos, quest_manager)
                if y_pos > MENU_BOTTOM:
                    break
            
            # Обрезаем и отображаем контент
            clipped_content = content_surface.subsurface(pygame.Rect(0, 0, WINDOW_SIZE[0], MENU_BOTTOM))
            self.screen.blit(clipped_content, (0, MENU_TOP), area=pygame.Rect(0, MENU_TOP, WINDOW_SIZE[0], MENU_BOTTOM - MENU_TOP))
            
            # Кнопка обновления
            self.draw_refresh_button()
            
            if time.time() - start_time >= TIMER_DURATION:
                quest_manager.load_quests_async(quest_manager)
                start_time = time.time()

            
            pygame.display.flip()
            clock.tick(60)

def main():
    res_mgr = ResourceManager()
    if not res_mgr.download_questlog():
        return
    
    quest_mgr = QuestManager(res_mgr)
    quest_mgr.load_quests()
    
    ui = GameUI()
    ui.main_loop(quest_mgr)

if __name__ == "__main__":
    main()
