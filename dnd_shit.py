import pygame
import sys
import configparser
import os
import requests
from pathlib import Path

# Helper function to get the path to the data directory
def get_data_path():
    if getattr(sys, 'frozen', False):  # Если файл упакован в .exe
        base_path = Path(sys._MEIPASS)  # Временная директория PyInstaller
    else:
        base_path = Path(__file__).parent  # Путь к файлу .py

    return base_path / "data"

data_path = get_data_path()
# Function to download questlog.ini
def download_questlog():
    servername_path = data_path / "servername"

    # Check if the servername file exists
    if not servername_path.exists():
        raise FileNotFoundError(f"Файл servername не найден в {servername_path}")

    # Read the URL from the servername file
    with open(servername_path, "r", encoding="utf-8") as file:
        url = file.read().strip()

    # Check if the URL is valid
    if not url.startswith("http"):
        raise ValueError("Некорректный URL в файле servername")

    # Get the path to save questlog.ini
    if getattr(sys, 'frozen', False):
        save_path = Path(sys.executable).parent / "questlog.ini"
    else:
        save_path = Path(__file__).parent / "questlog.ini"

    # Download the file
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Ошибка загрузки файла: {response.status_code}")

    # Save the file
    with open(save_path, "w", encoding="utf-8") as questlog_file:
        questlog_file.write(response.text)

    print(f"Файл questlog.ini успешно загружен и сохранён в {save_path}")


# Helper function to get the path to the questlog file
def get_questlog_path():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent

    questlog_path = base_path / "questlog.ini"
    if not questlog_path.exists():
        raise FileNotFoundError(f"Файл questlog.ini не найден в {questlog_path}")

    return questlog_path

# Function to read servername file and download questlog.ini
import time

# Call the download function
download_questlog()

# Initialize pygame
pygame.init()
# os.system("pause")
# Constants defining the game window and appearance
WINDOW_SIZE = (1000, 1000)
WINDOW_TITLE = "Fynn's spellbook"
icon = pygame.image.load(data_path / "icon.png") 
pygame.display.set_icon(icon)
BACKGROUND_IMAGE = data_path / "background.png"
MENU_IMAGE = data_path / "menu.png"
FONT_PATH = data_path / "determinationmonorusbylyajk.otf"
SYMBOL_FONT_PATH = data_path / "symbols_font.otf"
BUTTON_COLOR = (0, 0, 0)
BUTTON_BORDER_COLOR = (255, 255, 0)
BUTTON_TEXT_COLOR = (255, 255, 0)
TEXT_COLOR = (255, 255, 255)
YELLOW_COLOR = (255, 255, 0)
GREEN_COLOR = (0, 255, 0)
COMPLETED_COLOR = (127, 133, 32)  # Color for completed quests
FAILED_COLOR = (84, 84, 84)  # Color for failed quests
IN_PROGRESS_COLOR = (51, 253, 255)  # Color for quests in progress
GRAY_COLOR = (84, 84, 84)
BUTTON_HEIGHT = 45
BUTTON_WIDTH = 155
BUTTON_MARGIN = 20
HEADER_FONT_SIZE = 95
CATEGORY_FONT_SIZE = 50
TITLE_FONT_SIZE = 36
DESCRIPTION_FONT_SIZE = 24
STEP_FONT_SIZE = 24
REWARDS_FONT_SIZE = 24
AFTER_COMPLETION_FONT_SIZE = 36
DESCRIPTION_BOX_WIDTH = 699
DESCRIPTION_BOX_HEIGHT = 85
SCROLL_SPEED = 80
MENU_TOP = 182
MENU_BOTTOM = 924

# Preload fonts
FONTS = {
    "header": pygame.font.Font(FONT_PATH, HEADER_FONT_SIZE),
    "category": pygame.font.Font(FONT_PATH, CATEGORY_FONT_SIZE),
    "title": pygame.font.Font(FONT_PATH, TITLE_FONT_SIZE),
    "description": pygame.font.Font(FONT_PATH, DESCRIPTION_FONT_SIZE),
    "step": pygame.font.Font(FONT_PATH, STEP_FONT_SIZE),
    "rewards": pygame.font.Font(FONT_PATH, REWARDS_FONT_SIZE),
    "after_completion": pygame.font.Font(FONT_PATH, AFTER_COMPLETION_FONT_SIZE),
    "symbol": pygame.font.Font(SYMBOL_FONT_PATH, STEP_FONT_SIZE),
}

# Set up the display
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption(WINDOW_TITLE)

# Load resources
background = pygame.image.load(BACKGROUND_IMAGE)
menu = pygame.image.load(MENU_IMAGE)

# Helper function to render text within a box
def render_text_in_box(text, font, color, x, y, box_width, box_height, surface):
    """
    Splits a block of text into multiple lines to fit within a specified box size.
    Displays the lines on the given surface.
    """
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= box_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    y_offset = y
    for line in lines:
        if y_offset + font.size(line)[1] > y + box_height:
            break
        line_surface = font.render(line, True, color)
        surface.blit(line_surface, (x, y_offset))
        y_offset += font.size(line)[1]

    return y_offset

# Event class for managing callbacks
class Event:
    """
    Represents a custom event system with multiple callbacks.
    """
    def __init__(self):
        self.callbacks = []

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def trigger(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

# Base class for interactive elements
class Interactable:
    """
    Represents an interactable object, such as a button.
    """
    def __init__(self, x, y, width, height, event):
        self.rect = pygame.Rect(x, y, width, height)
        self.event = event

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.event.trigger()

    def render(self, screen):
        pass

# Text-based button with optional category and quest association
class TextButton(Interactable):
    """
    A button that displays text and triggers events for categories or quests.
    """
    def __init__(self, x, y, width, height, text, font, color, event, category=None, quest=None):
        super().__init__(x, y, width, height, event)
        self.text = text
        self.font = font
        self.color = color
        self.category = category
        self.quest = quest

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.category:
                    self.event.trigger(self.category)
                elif self.quest:
                    self.event.trigger(self.quest)

    def render(self, screen):
        text_surface = self.font.render(self.text, True, self.color)
        screen.blit(text_surface, (self.rect.x, self.rect.y))

# Simple button with predefined dimensions and text
class Button(Interactable):
    """
    Represents a basic button with text and a triggered event.
    """
    def __init__(self, x, y, width, height, text, font, event):
        super().__init__(x, y, width, height, event)
        self.text = text
        self.font = font

    def render(self, screen):
        pygame.draw.rect(screen, BUTTON_COLOR, self.rect)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, self.rect, 2)
        text_surface = self.font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

# Manage quests and event handling
class EventManager:
    """
    Handles quest loading, toggling categories, and quests visibility.
    """
    def __init__(self):
        self.quests = []
        self.hidden_categories = set()
        self.hidden_quests = set()

    def get_category_status(self, category):
        """Возвращает статус категории на основе статусов связанных квестов."""
        category_quests = [q for q in self.quests if q.category == category]
        if all(all(step["status"] == -1 for step in q.steps) for q in category_quests):
            return "failed"
        elif all(all(step["status"] in {1, -1} for step in q.steps) for q in category_quests):
            return "completed"
        else:
            return "in_progress"

    def refresh_event(self):
        download_questlog()
        print("Refresh event triggered!")
        self.load_quests()

    def load_quests(self):
        """
        Reads quests from a configuration file and stores them in the manager.
        """
        quest_file = get_questlog_path()
        if not os.path.exists(quest_file):
            print("Quest file not found.")
            return

        config = configparser.ConfigParser()
        config.read(quest_file, encoding="utf-8")

        self.quests = []
        for section in config.sections():
            if config.has_option(section, "category"):
                category = config.get(section, "category")
                # Пропустить квест, если категория равна "hidden"
                if "*" in category:
                    continue
                steps = []
                steps_data = config.get(section, "steps", fallback="").split(",")
                for step in steps_data:
                    text, status = step.split(":")
                    steps.append({"text": text.strip(), "status": int(status)})

                quest = Quest(
                    name=section,
                    category=config.get(section, "category"),
                    description=config.get(section, "description", fallback="No description."),
                    steps=steps,
                    rewards=config.get(section, "rewards", fallback="").split(",")
                )
                self.quests.append(quest)
        print("Loaded quests:", [q.name for q in self.quests])

# Modify Quest rendering to respect toggled categories and quests
class Quest:
    """
    Represents a quest with a category, description, steps, and rewards.
    Handles rendering and state checking.
    """
    def __init__(self, name, category, description, steps, rewards):
        self.name = name
        self.category = category
        self.description = description
        self.steps = steps
        self.rewards = rewards
    def render(self, screen, y_offset, last_rendered_category, clipping_rect, event_manager):
        surface = pygame.Surface((WINDOW_SIZE[0], WINDOW_SIZE[1]), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # Skip rendering if the y_offset exceeds the limit
        if y_offset > MENU_BOTTOM:
            return y_offset, last_rendered_category

        # If the category has not been rendered yet
        if self.category != last_rendered_category:
            category_status = event_manager.get_category_status(self.category)
            if category_status == "completed":
                category_text = f"{self.category} (выполнено)"
                category_color = COMPLETED_COLOR
            elif category_status == "failed":
                category_text = f"{self.category} (провалено)"
                category_color = FAILED_COLOR
            else:
                category_text = self.category
                category_color = YELLOW_COLOR

            text_width, text_height = FONTS["category"].size(category_text)
            category_event = Event()
            category_event.add_callback(lambda: event_manager.toggle_category(self.category))
            category_button = TextButton(
                x=104, 
                y=y_offset, 
                width=text_width, 
                height=text_height, 
                text=category_text, 
                font=FONTS["category"], 
                color=category_color, 
                event=category_event
            )
            category_button.render(surface)
            y_offset += CATEGORY_FONT_SIZE + 10
            last_rendered_category = self.category

            if category_status in {"completed", "failed"}:
                clipped_surface = surface.subsurface(clipping_rect)
                screen.blit(clipped_surface, (0, MENU_TOP))
                return y_offset, last_rendered_category

        if event_manager.get_category_status(self.category) in {"completed", "failed"}:
            return y_offset, last_rendered_category

        quest_event = Event()
        quest_event.add_callback(lambda: event_manager.toggle_quest(self.name))

        all_completed = all(step["status"] == 1 for step in self.steps)
        all_failed = all(step["status"] == -1 for step in self.steps)
        has_incomplete = any(step["status"] == 0 for step in self.steps)

        if all_completed:
            quest_title = f"{self.name} (выполнено)"
            quest_color = COMPLETED_COLOR
        elif all_failed:
            quest_title = f"{self.name} (провалено)"
            quest_color = FAILED_COLOR
        elif has_incomplete:
            quest_title = self.name
            quest_color = IN_PROGRESS_COLOR
        else:
            quest_title = self.name
            quest_color = TEXT_COLOR

        text_width, text_height = FONTS["title"].size(quest_title)
        quest_text = TextButton(
            x=143, 
            y=y_offset, 
            width=text_width, 
            height=text_height, 
            text=quest_title, 
            font=FONTS["title"], 
            color=quest_color, 
            event=quest_event
        )
        quest_text.render(surface)
        y_offset += TITLE_FONT_SIZE + 10

        if not all_completed and not all_failed:
            y_offset = render_text_in_box(
                self.description, FONTS["description"], TEXT_COLOR, 143, y_offset,
                DESCRIPTION_BOX_WIDTH, DESCRIPTION_BOX_HEIGHT, surface
            ) + 10

            for step in self.steps:
                if "*" in step["text"]:
                    continue
                status = step["status"]
                symbol_color = YELLOW_COLOR if status == 0 else (GREEN_COLOR if status == 1 else GRAY_COLOR)
                symbol = "[!]" if status == 0 else ("[V]" if status == 1 else "[X]")
                symbol_surface = FONTS["symbol"].render(symbol, True, symbol_color)
                step_surface = FONTS["step"].render(f" {step['text']}", True, TEXT_COLOR)
                surface.blit(symbol_surface, (143, y_offset))
                surface.blit(step_surface, (173, y_offset))
                y_offset += STEP_FONT_SIZE + 10

            if self.rewards:
                after_completion_text = FONTS["after_completion"].render("После выполнения", True, TEXT_COLOR)
                surface.blit(after_completion_text, (143, y_offset))
                y_offset += AFTER_COMPLETION_FONT_SIZE + 10

                for reward in self.rewards:
                    reward_text = FONTS["rewards"].render(f"* {reward}", True, TEXT_COLOR)
                    surface.blit(reward_text, (143, y_offset))
                    y_offset += REWARDS_FONT_SIZE + 10

        clipped_surface = surface.subsurface(clipping_rect)
        screen.blit(clipped_surface, (0, MENU_TOP))

        return y_offset, last_rendered_category

# Main game loop
def main():
    """
    The main game loop that handles rendering, events, and updates.
    """
    clock = pygame.time.Clock()
    event_manager = EventManager()
    event_manager.refresh_event()

    refresh_event = Event()
    refresh_event.add_callback(event_manager.refresh_event)

    refresh_button = Button(
        x=WINDOW_SIZE[0] - BUTTON_WIDTH - 5,
        y=WINDOW_SIZE[1] - BUTTON_HEIGHT - 5,
        width=BUTTON_WIDTH,
        height=BUTTON_HEIGHT,
        text="Обновить",
        font=FONTS["title"],
        event=refresh_event
    )

    scroll_offset = 0
    running = True
    while running:
        for event in pygame.event.get():
            # Handle category and quest buttons
            for quest in event_manager.quests:
                for section in [quest.category, quest.name]:
                    if isinstance(section, TextButton):
                        section.handle_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    scroll_offset = max(scroll_offset - SCROLL_SPEED, 0)
                elif event.button == 5:  # Scroll down
                    scroll_offset += SCROLL_SPEED

                refresh_button.handle_event(event)

        # Draw the background
        screen.blit(background, (0, 0))

        # Draw the menu
        menu_rect = menu.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2))
        screen.blit(menu, menu_rect)

        # Render header
        header_surface = FONTS["header"].render("Квесты", True, TEXT_COLOR)
        screen.blit(header_surface, (108, 98))

        # Render quests
        clipping_rect = pygame.Rect(0, MENU_TOP, WINDOW_SIZE[0], MENU_BOTTOM - MENU_TOP)
        y_offset = 175 - scroll_offset
        last_rendered_category = None
        for quest in event_manager.quests:
            y_offset, last_rendered_category = quest.render(screen, y_offset + 20, last_rendered_category, clipping_rect, event_manager)

        # Render refresh button
        refresh_button.render(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
