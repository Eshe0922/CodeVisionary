# Contributing to CodeVisionary

Thank you for your interest in contributing to CodeVisionary! We welcome contributions from the community to help make this project better.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct principles:
- Be respectful and inclusive
- Exercise consideration and empathy in your speech and actions
- Focus on what is best for the community
- Show courtesy and respect towards other community members

## How to Contribute

### 1. Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CodeVisionary.git
   ```
3. Build the Docker image:
    ```bash
    cd docker
    docker build -t codevisionary.evaluate .
    docker pull eshe1836316339/codevisionary:lint
    docker tag eshe1836316339/codevisionary:lint codevisionary.lint 
    ```
4. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   npm install --save-dev prettier
   apt-get install pandoc
   apt-get install texlive-xetex
   ```

### 2. Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes following our coding conventions:
   - Use clear, descriptive variable and function names
   - Write docstrings for new functions and classes
   - Add comments for complex logic
   - Follow PEP 8 style guidelines for Python code
   - Keep functions focused and single-purpose
   - Add appropriate error handling

3. Test your changes:
   - Ensure all existing tests pass
   - Add new tests for new functionality
   - Verify Docker-based builds work correctly

### 3. Submitting Changes

1. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "Description of your changes"
   ```

2. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Open a Pull Request:
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots or examples if applicable
   - List any breaking changes

### 4. Pull Request Process

1. Your PR will be reviewed by maintainers
2. Address any requested changes or feedback
3. Once approved, your PR will be merged
4. Celebrate your contribution! 🎉

## Development Guidelines

### Project Structure
- Place new agent implementations in `agents/`
- Add utility functions to `utils/`
- Docker-related changes go in `docker/`
- Main functionality should be in appropriate modules

### Testing
- Write unit tests for new functionality
- Include integration tests for Docker-related features
- Test edge cases and error conditions
- Ensure tests are deterministic

### Documentation
- Update README.md for significant changes
- Add docstrings to new classes and functions
- Include example usage where appropriate
- Document any new dependencies

### Best Practices
- Handle errors gracefully with meaningful messages
- Log important operations and state changes
- Consider backward compatibility
- Follow security best practices

## Getting Help

- Open an issue for bugs or feature requests
- Ask questions in pull requests
- Check existing issues and documentation

## License

By contributing to CodeVisionary, you agree that your contributions will be licensed under the MIT License.