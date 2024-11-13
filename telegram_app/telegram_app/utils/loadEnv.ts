export function loadEnvVariable(name: string): string {
    const value = process.env[name];
    if (!value) {
        console.error(`Environment variable ${name} is missing.`);
        process.exit(1);
    }
    return value;
}

