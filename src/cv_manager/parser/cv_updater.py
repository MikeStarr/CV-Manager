import os
from docx import Document

class CVUpdater:
    """Updates a .docx file while preserving paragraph styles."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = Document(file_path)

    def update_paragraph_text(self, target_text: str, new_text: str) -> bool:
        """
        Finds a paragraph containing the exact target_text and replaces it with new_text,
        preserving the style of the original paragraph.
        """
        found = False
        for para in self.doc.paragraphs:
            if para.text.strip() == target_text.strip():
                # We replace the text but keep the paragraph object and its style
                para.text = new_text
                found = True
                break
        return found

    def save(self, output_path: str = None):
        """Saves the modified document."""
        target = output_path if output_path else self.file_path
        self.doc.save(target)

if __name__ == "__main__":
    # Test the updater (requires a sample docx in cvs/)
    import os
    test_file = "cvs/test_cv.docx"
    if os.path.exists(test_file):
        updater = CVUpdater(test_file)
        # This is a very simple test: try to replace a known string
        # In a real scenario, we'd use the parsed structure from Phase 1
        success = updater.update_paragraph_text("Old Text", "New Updated Text")
        if success:
            updater.save(test_file)
            print("Update successful")
        else:
            print("Target text not found")
    else:
        print("No test file found in cv.test_cv.docx")
