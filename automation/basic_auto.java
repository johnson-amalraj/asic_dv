import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.By;
import java.time.Duration;

public class BasicAuto {
    public static void main(String[] args) {
        WebDriver driver = null;
        
        try {
            // Initialize Chrome options
            ChromeOptions options = new ChromeOptions();
            options.addArguments("--incognito");
            System.out.println("Setting up Chrome in incognito mode...");
            
            // Create WebDriver instance
            driver = new ChromeDriver(options);
            System.out.println("WebDriver initialized successfully");
            
            // Set implicit wait
            driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(10));
            System.out.println("Implicit wait set to 10 seconds");
            
            // Navigate to website
            driver.get("https://www.example.com");
            System.out.println("Navigated to https://www.example.com");
            
            // Get and print page title
            String pageTitle = driver.getTitle();
            System.out.println("Page title: " + pageTitle);
            
            // Validate page loaded correctly
            assert pageTitle.contains("Example") : "Page title mismatch";
            System.out.println("Page loaded successfully!");
            
            // Example: Wait for and interact with an element
            WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
            WebElement element = wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("h1")));
            System.out.println("Found element: " + element.getText());
            
            // Add more test steps here as needed
            Thread.sleep(3000); // Wait 3 seconds to see the browser
            
            System.out.println("Test execution completed successfully");
            
        } catch (Exception e) {
            System.err.println("An error occurred: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // Close the driver
            if (driver != null) {
                driver.quit();
                System.out.println("WebDriver closed successfully");
            }
        }
    }
}   