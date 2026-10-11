package example.boot.bootstrap;

@org.springframework.boot.autoconfigure.SpringBootApplication(scanBasePackages = "example.boot")
public class Application {
    public static void main(String[] args) {
        org.springframework.boot.SpringApplication.run(Application.class, args);
    }
}
